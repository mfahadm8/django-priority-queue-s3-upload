from django.shortcuts import render
from django.http import JsonResponse
import redis

r = redis.Redis()

def change_upload_priority(request, upload_id, priority):
    # Assuming 'upload_id' is the file path or some unique identifier
    study_info = None
    for item in r.zrange('upload_queue', 0, -1, withscores=False):
        if eval(item).get('guid') == upload_id:
            study_info = item
            break
    if study_info:
        r.zadd('upload_queue', {study_info: priority})
        return JsonResponse({'status': 'priority changed'})
    return JsonResponse({'status': 'not found'})

def pause_upload(request, upload_id):
    # Pause by removing from queue
    study_info = None
    for item in r.zrange('upload_queue', 0, -1, withscores=False):
        if eval(item).get('guid') == upload_id:
            study_info = item
            break
    if study_info:
        r.zrem('upload_queue', study_info)
        r.hset('paused_uploads', upload_id, study_info)
        return JsonResponse({'status': 'paused'})
    return JsonResponse({'status': 'not found'})

def resume_upload(request, upload_id):
    # Resume by adding back to queue
    study_info = r.hget('paused_uploads', upload_id)
    if study_info:
        r.zadd('upload_queue', {study_info: 0})  # Default priority
        r.hdel('paused_uploads', upload_id)
        return JsonResponse({'status': 'resumed'})
    return JsonResponse({'status': 'not found'})

def cancel_upload(request, upload_id):
    # Cancel by removing from queue
    study_info = None
    for item in r.zrange('upload_queue', 0, -1, withscores=False):
        if eval(item).get('guid') == upload_id:
            study_info = item
            break
    if study_info:
        r.zrem('upload_queue', study_info)
        return JsonResponse({'status': 'canceled'})
    return JsonResponse({'status': 'not found'})
