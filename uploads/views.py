# uploads/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import FileUpload
from django.conf import settings
from django.core.cache import cache
from .serializers import FileUploadSerializer, UpdatePrioritySerializer, UpdateStatusSerializer

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
            priority = serializer.validated_data['priority']
            file_upload = FileUpload.get(guid)
            if file_upload:
                old_priority = file_upload.priority
                file_upload.priority = priority
                file_upload.save()

                # Adjust priorities if necessary
                if priority <= settings.MAX_UPLOADS:
                    if file_upload.status == 'paused':
                        file_upload.status = 'queued'
                        file_upload.save()
                else:
                    if file_upload.status == 'uploading':
                        file_upload.status = 'paused'
                        file_upload.save()
                
                return Response({'status': 'priority updated'})
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def update_status(self, request):
        serializer = UpdateStatusSerializer(data=request.data)
        if serializer.is_valid():
            guid = serializer.validated_data['guid']
            status = serializer.validated_data['status']
            file_upload = FileUpload.get(guid)
            if file_upload:
                if status == 'paused':
                    queued_uploads = FileUpload.filter(status='queued')
                    if queued_uploads:
                        last_item = max(queued_uploads, key=lambda x: x.priority)
                        file_upload.priority, last_item.priority = last_item.priority, file_upload.priority
                        last_item.save()
                    file_upload.status = 'paused'
                elif status == 'resume':
                    file_upload.status = 'queued'
                elif status == 'cancel':
                    file_upload.status = 'canceled'
                file_upload.save()
                return Response({'status': 'status updated'})
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
