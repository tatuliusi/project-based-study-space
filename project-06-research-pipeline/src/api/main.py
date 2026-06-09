import asyncio
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from src.scheduler.scheduler import (
    add_schedule,
    list_schedules,
    remove_schedule,
    scheduler,
)
from src.services.redis_service import (
    create_job,
    get_job_status,
    get_report_json,
    get_report_pdf,
    set_job_status,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Research-to-Report Pipeline", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ReportRequest(BaseModel):
    topic: str


class ReportResponse(BaseModel):
    job_id: str
    status: str


class ScheduleRequest(BaseModel):
    topic: str
    cron: str


class ScheduleResponse(BaseModel):
    schedule_id: str
    topic: str
    cron: str


# ---------------------------------------------------------------------------
# Background task: run the full pipeline
# ---------------------------------------------------------------------------

async def _run_pipeline(job_id: str, topic: str) -> None:
    from src.graph.pipeline import pipeline

    await set_job_status(job_id, "running")
    try:
        initial_state = {
            "job_id": job_id,
            "topic": topic,
            "sub_topics": [],
            "findings": [],
            "fact_check_results": [],
            "report": None,
            "artifact_url": None,
            "status": "running",
            "error": None,
        }
        await pipeline.ainvoke(initial_state)
    except Exception as exc:
        logger.exception("Pipeline failed for job %s: %s", job_id, exc)
        await set_job_status(job_id, "failed", error=str(exc))


# ---------------------------------------------------------------------------
# Routes — reports
# ---------------------------------------------------------------------------

@app.post("/reports", response_model=ReportResponse, status_code=202)
async def submit_report(req: ReportRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    await create_job(job_id, req.topic)
    background_tasks.add_task(_run_pipeline, job_id, req.topic)
    return ReportResponse(job_id=job_id, status="queued")


@app.get("/reports/{job_id}/status")
async def get_status(job_id: str):
    meta = await get_job_status(job_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return meta


@app.get("/reports/{job_id}")
async def get_report(job_id: str):
    data = await get_report_json(job_id)
    if data is None:
        meta = await get_job_status(job_id)
        if meta is None:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=202, detail=f"Job status: {meta.get('status')}")
    return data


@app.get("/reports/{job_id}/pdf")
async def get_pdf(job_id: str):
    pdf = await get_report_pdf(job_id)
    if pdf is None:
        meta = await get_job_status(job_id)
        if meta is None:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(status_code=202, detail=f"Job status: {meta.get('status')}")
    return Response(content=pdf, media_type="application/pdf")


# ---------------------------------------------------------------------------
# Routes — schedules
# ---------------------------------------------------------------------------

@app.post("/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(req: ScheduleRequest):
    schedule_id = str(uuid.uuid4())
    try:
        add_schedule(schedule_id, req.topic, req.cron)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return ScheduleResponse(schedule_id=schedule_id, topic=req.topic, cron=req.cron)


@app.get("/schedules")
async def get_schedules():
    return list_schedules()


@app.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: str):
    removed = remove_schedule(schedule_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Schedule not found")
