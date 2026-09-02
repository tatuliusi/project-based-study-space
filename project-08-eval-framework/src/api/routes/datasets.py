from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.schemas import AddSamplesRequest, CreateDatasetRequest
from src.models import Dataset

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _bump_version(version: str) -> str:
    parts = version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


@router.post("", response_model=Dataset, status_code=201)
async def create_dataset(req: CreateDatasetRequest, request: Request) -> Dataset:
    db = request.app.state.db
    dataset = Dataset(
        name=req.name,
        description=req.description,
        metric_set=req.metric_set,
        samples=req.samples,
    )
    await db.save_dataset(dataset)
    return dataset


@router.get("", response_model=list[Dataset])
async def list_datasets(request: Request) -> list[Dataset]:
    db = request.app.state.db
    return await db.list_datasets()


@router.get("/{dataset_id}", response_model=Dataset)
async def get_dataset(dataset_id: str, request: Request) -> Dataset:
    db = request.app.state.db
    dataset = await db.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="dataset not found")
    return dataset


@router.post("/{dataset_id}/samples", response_model=Dataset)
async def add_samples(dataset_id: str, req: AddSamplesRequest, request: Request) -> Dataset:
    db = request.app.state.db
    dataset = await db.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="dataset not found")
    dataset.samples.extend(req.samples)
    dataset.version = _bump_version(dataset.version)
    await db.save_dataset(dataset)
    return dataset
