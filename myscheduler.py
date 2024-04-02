import fastapi
import pydantic
import uvicorn

from apscheduler.schedulers.background import BackgroundScheduler


class JobModel(pydantic.BaseModel):
    id: str
    name: str


scheduler = BackgroundScheduler()


def job():
    print('job is running')

scheduler.add_job(job, 'interval', seconds=3, id='first-job-id')
scheduler.start()

# jobs = scheduler.get_jobs()
# job = jobs[0]
# import IPython
# IPython.embed()
# import sys
# sys.exit()


app = fastapi.FastAPI()
@app.get('/jobs')
async def list_jobs(r: fastapi.Request) -> dict:
    jobs = scheduler.get_jobs()
    jobs = [JobModel(id=j.id, name=j.name).model_dump() for j in jobs]
    return fastapi.responses.JSONResponse(jobs)


uvicorn.run(app)
