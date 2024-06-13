# uploads/serializers.py

from rest_framework import serializers
from .models import FileUpload

class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileUpload
        fields = '__all__'

class UpdatePrioritySerializer(serializers.Serializer):
    guid = serializers.CharField(max_length=255)
    priority = serializers.IntegerField()

class UpdateStatusSerializer(serializers.Serializer):
    guid = serializers.CharField(max_length=255)
    status = serializers.CharField(max_length=20)
