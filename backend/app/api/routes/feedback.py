from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_selection_feedback_service
from app.application.selection_feedback_service import SelectionFeedbackService

router = APIRouter(prefix="/api/v1", tags=["feedback"])


class SelectionEvent(BaseModel):
    result_id: str


@router.post("/feedback/select", status_code=204)
def record_selection(
    event: SelectionEvent,
    service: SelectionFeedbackService = Depends(get_selection_feedback_service),
) -> None:
    service.record_selection(event.result_id)
