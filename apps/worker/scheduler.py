"""Scheduler de réplica única, protegido por lease no Redis."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.platform.cache.redis_client import criar_cliente
from app.platform.config.settings import Settings, get_settings
from app.platform.db.engine import criar_engine
from app.platform.db.session.session_factory import criar_fabrica_de_sessoes
from app.platform.observability.logging import configurar_logging
from app.platform.storage.object_storage import criar_cliente as criar_storage
from worker.jobs.backup.database_backup import backup_exists_today, create_database_backup
from worker.jobs.backup.restore_drill import restore_drill_exists_on, run_restore_drill
from worker.jobs.integrity.check_f2_integrity import executar as verificar_integridade
from worker.jobs.retention.cleanup import execute as cleanup_retention

TICK_SEGUNDOS = 60
LOCK_SEGUNDOS = 90
CHAVE_DE_LIDER = "rfbalance:scheduler:leader"

_logger = structlog.get_logger("scheduler")


async def executar() -> None:
    settings = get_settings()
    settings.validar()
    configurar_logging(settings.app.log_level, settings.app.app_env)

    redis = criar_cliente(settings.redis)
    engine = criar_engine(settings.database)
    sessoes = criar_fabrica_de_sessoes(engine)
    token = uuid.uuid4().hex
    storage = criar_storage(settings.storage)
    ultimo_backup: date | None = None
    ultima_tentativa_backup: datetime | None = None
    ultimo_ensaio_restauracao: date | None = None
    ultima_tentativa_restauracao: datetime | None = None
    ultima_limpeza: date | None = None
    _logger.info("scheduler_iniciado", environment=settings.app.app_env)
    try:
        while True:
            adquiriu = await redis.set(CHAVE_DE_LIDER, token, ex=LOCK_SEGUNDOS, nx=True)
            if adquiriu:
                async with sessoes() as session:
                    resultados = await verificar_integridade(session)
                ultima_limpeza = await _executar_limpeza_se_devida(
                    settings, sessoes, storage, ultima_limpeza
                )
                ultimo_backup, ultima_tentativa_backup = await _executar_backup_se_devido(
                    settings, ultimo_backup, ultima_tentativa_backup
                )
                (
                    ultimo_ensaio_restauracao,
                    ultima_tentativa_restauracao,
                ) = await _executar_ensaio_restauracao_se_devido(
                    settings, ultimo_ensaio_restauracao, ultima_tentativa_restauracao
                )
                _logger.info("scheduler_tick", scheduled_jobs=3, leader=True, **resultados)
            elif await redis.get(CHAVE_DE_LIDER) == token:
                await redis.expire(CHAVE_DE_LIDER, LOCK_SEGUNDOS)
                async with sessoes() as session:
                    resultados = await verificar_integridade(session)
                ultima_limpeza = await _executar_limpeza_se_devida(
                    settings, sessoes, storage, ultima_limpeza
                )
                ultimo_backup, ultima_tentativa_backup = await _executar_backup_se_devido(
                    settings, ultimo_backup, ultima_tentativa_backup
                )
                (
                    ultimo_ensaio_restauracao,
                    ultima_tentativa_restauracao,
                ) = await _executar_ensaio_restauracao_se_devido(
                    settings, ultimo_ensaio_restauracao, ultima_tentativa_restauracao
                )
                _logger.info("scheduler_tick", scheduled_jobs=3, leader=True, **resultados)
            else:
                _logger.info("scheduler_standby", leader=False)
            await asyncio.sleep(TICK_SEGUNDOS)
    finally:
        if await redis.get(CHAVE_DE_LIDER) == token:
            await redis.delete(CHAVE_DE_LIDER)
        await redis.aclose()
        await engine.dispose()


async def _executar_backup_se_devido(
    settings: Settings,
    ultimo_backup: date | None,
    ultima_tentativa: datetime | None,
) -> tuple[date | None, datetime | None]:
    storage = settings.storage
    agora = datetime.now(UTC)
    if not storage.backup_bucket or agora.hour < storage.backup_hour_utc:
        return ultimo_backup, ultima_tentativa
    if ultimo_backup == agora.date():
        return ultimo_backup, ultima_tentativa
    if ultima_tentativa and agora - ultima_tentativa < timedelta(minutes=15):
        return ultimo_backup, ultima_tentativa

    ultima_tentativa = agora
    try:
        existe = await asyncio.to_thread(backup_exists_today, settings, agora)
        if existe:
            _logger.info("backup_diario_ja_existia", data=str(agora.date()))
        else:
            resultado = await asyncio.to_thread(create_database_backup, settings, agora)
            _logger.info(
                "backup_diario_concluido",
                bucket=resultado.bucket,
                key=resultado.key,
                bytes=resultado.compressed_bytes,
                removed_by_retention=resultado.removed_by_retention,
            )
        ultimo_backup = agora.date()
    except Exception:
        _logger.exception("backup_diario_falhou")
    return ultimo_backup, ultima_tentativa


async def _executar_limpeza_se_devida(
    settings: Settings,
    sessoes: async_sessionmaker[AsyncSession],
    storage: object,
    ultima_limpeza: date | None,
) -> date | None:
    agora = datetime.now(UTC)
    if ultima_limpeza == agora.date() or agora.hour < settings.retention.retention_cleanup_hour_utc:
        return ultima_limpeza
    try:
        async with sessoes() as session:
            result = await cleanup_retention(
                session,
                storage=storage,
                storage_settings=settings.storage,
                retention=settings.retention,
                now=agora,
            )
        _logger.info("retention_cleanup_completed", **result)
        return agora.date()
    except Exception:
        _logger.exception("retention_cleanup_failed")
        return ultima_limpeza


async def _executar_ensaio_restauracao_se_devido(
    settings: Settings,
    ultimo_ensaio: date | None,
    ultima_tentativa: datetime | None,
) -> tuple[date | None, datetime | None]:
    storage = settings.storage
    agora = datetime.now(UTC)
    if (
        not storage.backup_bucket
        or agora.weekday() != storage.backup_restore_drill_weekday
        or agora.hour < storage.backup_restore_drill_hour_utc
    ):
        return ultimo_ensaio, ultima_tentativa
    if ultimo_ensaio == agora.date():
        return ultimo_ensaio, ultima_tentativa
    if ultima_tentativa and agora - ultima_tentativa < timedelta(minutes=30):
        return ultimo_ensaio, ultima_tentativa

    ultima_tentativa = agora
    try:
        existe = await asyncio.to_thread(restore_drill_exists_on, settings, agora)
        if existe:
            _logger.info("ensaio_restauracao_ja_existia", data=str(agora.date()))
        else:
            resultado = await asyncio.to_thread(run_restore_drill, settings)
            _logger.info(
                "ensaio_restauracao_concluido",
                backup_key=resultado.backup_key,
                report_key=resultado.report_key,
                table_count=resultado.table_count,
            )
        ultimo_ensaio = agora.date()
    except Exception:
        _logger.exception("ensaio_restauracao_falhou")
    return ultimo_ensaio, ultima_tentativa


if __name__ == "__main__":
    asyncio.run(executar())
