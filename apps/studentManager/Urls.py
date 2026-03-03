from django.urls import path
from .views import (
    StudentProgressionListView,
    StudentProgressionCreateView,
    StudentProgressionDetailView,
    bulk_promote,
    seed_class_progressions,
)

urlpatterns = [
    
    path('', StudentProgressionListView.as_view(), name='progression-list'),

    path('create/', StudentProgressionCreateView.as_view(), name='progression-create'),

    path('<int:pk>/', StudentProgressionDetailView.as_view(), name='progression-detail'),

    path('bulk-promote/', bulk_promote, name='progression-bulk-promote'),

    path('seed/', seed_class_progressions, name='progression-seed'),
]