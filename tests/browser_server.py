"""Test-only ASGI entry point. Production never accepts a client-supplied clock."""
from backend import main, service_adapters
from tests.support import RECOMMENDATION_TIME, datetime_at

service_adapters.datetime = datetime_at([RECOMMENDATION_TIME])
app = main.app


@app.middleware('http')
async def identify_fixture(request, call_next):
    response = await call_next(request)
    response.headers['X-Lotus-Test-Time'] = RECOMMENDATION_TIME.isoformat()
    return response
