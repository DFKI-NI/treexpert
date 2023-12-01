from ninja import NinjaAPI
from core.api import router as core_router

api = NinjaAPI(
    title="treexpert API",
    description="The treexpert provides an API to save, edit and run a decision tree.",
)

api.add_router("/core/", core_router)
