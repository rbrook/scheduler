import time

import pydantic

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore, MongoClient
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.mongodb import MongoClient 
from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor


# config
DB_NAME = 'apscheduler'

# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
class MongoDBLock:
    def __init__(self, mongo_db):
        self.collection = mongo_db.get_collection('locks')

    def acquire(self, lock_name):
        try:
            self.collection.insert_one({'_id': lock_name})
            return True
        except Exception as e:
            if "duplicate key error" in str(e):  # lock is taken!
                return False
            raise e

    def release(self, lock_name):
        self.collection.delete_one({'_id': lock_name})
        # wait a bit so that other concurrent triggers won't acquire
        time.sleep(0.2)


def _distributed_run(lock_manager):
    def decorator(func):
        func_name = func.__name__
        def wrapper(*args, **kwargs):
            if lock_manager.acquire(func_name):
                try:
                    return func(*args, **kwargs)
                finally:
                    lock_manager.release(func_name)
            else:
                return None
        
        return wrapper
        
        # job_name = func.__name__
        # job_location = func.__module__
        # jobs = scheduler.get_jobs(jobstore='default')
        # if not [j for j in jobs if j.id == job_name]:
        #     scheduler.add_job(wrapper, trigger=IntervalTrigger(seconds=5), id=job_name)
        # # scheduler.add_job(f"{job_location}:{job_name}", trigger=IntervalTrigger(seconds=5), id=job_name)
        
    # setattr(decorator, __name__, func_name)
    return decorator


def add_job(func_name, trigger):
    # job_name = func.__name__
    job_name = func_name
    jobs = scheduler.get_jobs(jobstore='default')
    if not [j for j in jobs if j.id == job_name]:
        scheduler.add_job(f"__main__:{job_name}", trigger=trigger, id=job_name, name=job_name)


def distributed_run(func):
    lock_manager = MongoDBLock(locks_db)
    def wrapper(*args, **kwargs):
        if lock_manager.acquire(func.__name__):
            try:
                return func(*args, **kwargs)
            finally:
                lock_manager.release(func.__name__)
        else:
            return None
    return wrapper


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = 
client = MongoClient()
locks_db = client.get_database(DB_NAME)
lock_manager = MongoDBLock(locks_db)

# Use Mongo as the job store
jobstore = {
    'default': MongoDBJobStore(database=DB_NAME, client=MongoClient())
}

job_defaults = {
    'coalesce': True,
    'max_instances': 1
}

executors = {
    'default': ThreadPoolExecutor(20),
    'processpool': ProcessPoolExecutor(5)
}


scheduler = BackgroundScheduler()
scheduler.configure(jobstores=jobstore, job_defaults=job_defaults, executors=executors)
scheduler.start()


@distributed_run
def foo_job():
    print('hello from foo job!', f"{time.time()}")
add_job('foo_job', trigger=IntervalTrigger(seconds=3))


# that's it - form here it's only FastAPI code
import uvicorn, fastapi
app = fastapi.FastAPI()
@app.get('/jobs')
async def list_jobs(r: fastapi.Request) -> dict:
    class JobModel(pydantic.BaseModel):
        id: str
        name: str

    return fastapi.responses.JSONResponse(
        [JobModel(id=j.id, name=j.name).model_dump() for j in scheduler.get_jobs(jobstore='default')]
        )


port=8000
while port<8010:
    try:
        uvicorn.run(app, port=port, reload=False)
    except KeyboardInterrupt:
        break
    except:
        port += 1
