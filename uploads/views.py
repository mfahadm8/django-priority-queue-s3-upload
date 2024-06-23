# uploads/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import FileUpload
from django.conf import settings
from .serializers import FileUploadSerializer, UpdatePrioritySerializer, UpdateStatusSerializer

class FileUploadViewSet(viewsets.ModelViewSet):
    queryset = FileUpload.objects.all()
    serializer_class = FileUploadSerializer

    @action(detail=False, methods=['post'])
    def update_priority(self, request):
        serializer = UpdatePrioritySerializer(data=request.data)
        if serializer.is_valid():
            guid = serializer.validated_data['guid']
            priority = serializer.validated_data['priority']
            try:
                file_upload = FileUpload.objects.get(guid=guid)
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
            except FileUpload.DoesNotExist:
                return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def update_status(self, request):
        serializer = UpdateStatusSerializer(data=request.data)
        if serializer.is_valid():
            guid = serializer.validated_data['guid']
            status = serializer.validated_data['status']
            try:
                file_upload = FileUpload.objects.get(guid=guid)
                if status == 'paused':
                    last_item = FileUpload.objects.filter(status='queued').order_by('priority').last()
                    if last_item:
                        file_upload.priority, last_item.priority = last_item.priority, file_upload.priority
                        last_item.save()
                    file_upload.status = 'paused'
                elif status == 'resume':
                    file_upload.status = 'queued'
                elif status == 'cancel':
                    file_upload.status = 'canceled'
                file_upload.save()
                return Response({'status': 'status updated'})
            except FileUpload.DoesNotExist:
                return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
