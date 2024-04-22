from __future__ import absolute_import

from mq.celery import app


@app.task
def analysis_task(fid):
    return fid


@app.task
def compile_task(fid):
    return fid


@app.task
def ml_analysis_task(fid):
    return fid
