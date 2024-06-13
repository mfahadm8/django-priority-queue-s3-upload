# uploads/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import FileUpload
from .serializers import FileUploadSerializer, UpdatePrioritySerializer, UpdateStatusSerializer
import redis

r = redis.Redis()

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
                file_upload.priority = priority
                file_upload.save()
                r.zadd(file_upload.queue_name, {str(file_upload): priority})
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
                file_upload.status = status
                file_upload.save()
                return Response({'status': 'status updated'})
            except FileUpload.DoesNotExist:
                return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
