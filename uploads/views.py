# uploads/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings
from .models import FileUpload
from .serializers import FileUploadSerializer, UpdatePrioritySerializer, UpdateStatusSerializer
from django.core.cache import cache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PRIORITY_LEVELS = {
    'highest': 1,
    'high': 2,
    'medium': 3,
    'low': 4,
    'lowest': 5,
}

class FileUploadViewSet(viewsets.ViewSet):
    """
    A simple ViewSet for listing, retrieving, updating, and deleting FileUploads.
    """

    def list(self, request):
        file_uploads = [FileUpload.get(key) for key in cache.keys('*') if FileUpload.get(key)]
        serializer = FileUploadSerializer(file_uploads, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        file_upload = FileUpload.get(pk)
        if file_upload:
            serializer = FileUploadSerializer(file_upload)
            return Response(serializer.data)
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file_upload = FileUpload(**serializer.validated_data)
            file_upload.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        file_upload = FileUpload.get(pk)
        if file_upload:
            serializer = FileUploadSerializer(file_upload, data=request.data)
            if serializer.is_valid():
                file_upload = FileUpload(**serializer.validated_data)
                file_upload.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        if FileUpload.exists(pk):
            cache.delete(pk)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def update_priority(self, request):
        serializer = UpdatePrioritySerializer(data=request.data)
        if serializer.is_valid():
            guid = serializer.validated_data['guid']
            priority_label_or_level = serializer.validated_data['priority']
            
            # Handle both integer levels and string labels
            if isinstance(priority_label_or_level, int):
                new_priority = priority_label_or_level
            else:
                new_priority = PRIORITY_LEVELS.get(priority_label_or_level)
                if new_priority is None:
                    return Response({'error': 'Invalid priority label'}, status=status.HTTP_400_BAD_REQUEST)

            file_upload = FileUpload.get(guid)
            logger.info("1")
            logger.info(guid)
            if file_upload:
                # Fetch all file uploads
                all_uploads = FileUpload.all()

                # Check if we need to pause any running tasks
                if priority_label_or_level == 'highest' or new_priority == 1 or new_priority > max(upload.priority for upload in all_uploads):
                    currently_uploading = [upload for upload in all_uploads if upload.status == 'uploading']
                    # Sort the current uploading tasks by priority in descending order (least priority first)
                    currently_uploading.sort(key=lambda x: x.priority, reverse=True)
                    to_pause = currently_uploading[:max(0, len(currently_uploading) - settings.MAX_UPLOADS + 1)]
                    logger.info("To Pause")
                    logger.info(to_pause)
                    for upload in to_pause:
                        logger.info(f"Pausing upload for {upload.guid}")
                        logger.info(upload.to_dict())
                        upload.status = 'paused'
                        upload.save()

                # Ensure unique priorities by shifting others
                for upload in all_uploads:
                    if upload.priority >= new_priority:
                        upload.priority += 1
                        upload.save()

                # Update the priority of the target file upload
                file_upload.priority = new_priority
                file_upload.status = 'queued' if new_priority == 1 else file_upload.status
                file_upload.save()

                return Response({'status': 'priority updated'})
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=False, methods=['post'])
    def update_status(self, request):
        serializer = UpdateStatusSerializer(data=request.data)
        if serializer.is_valid():
            guid = serializer.validated_data['guid']
            file_upload_status = serializer.validated_data['status']
            file_upload = FileUpload.get(guid)
            if file_upload:
                if file_upload_status == 'paused':
                    queued_uploads = FileUpload.filter(status='queued')
                    if queued_uploads:
                        last_item = max(queued_uploads, key=lambda x: x.priority) # swap priority with queued task of least priority
                        file_upload.priority, last_item.priority = last_item.priority, file_upload.priority
                        last_item.save()
                    file_upload.status = 'paused'
                elif file_upload_status == 'resume':
                    file_upload.status = 'queued'
                elif file_upload_status == 'cancel':
                    file_upload.status = 'canceled'
                file_upload.save()
                return Response({'status': 'status updated'})
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
