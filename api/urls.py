from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    ProductViewSet, IngredientViewSet, SkinConcernViewSet,
    IngredientUmbrellaViewSet, ArticleViewSet,
    RoutineViewSet, RoutineItemViewSet,
    ClickEventCreateView,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'ingredients', IngredientViewSet, basename='ingredient')
router.register(r'concerns', SkinConcernViewSet, basename='concern')
router.register(r'umbrellas', IngredientUmbrellaViewSet, basename='umbrella')
router.register(r'articles', ArticleViewSet, basename='article')
router.register(r'routines', RoutineViewSet, basename='routine')

urlpatterns = [
    path('', include(router.urls)),
    # Nested routine items: /api/routines/{id}/items/
    path(
        'routines/<int:routine_pk>/items/',
        RoutineItemViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='routine-items-list',
    ),
    path(
        'routines/<int:routine_pk>/items/<int:pk>/',
        RoutineItemViewSet.as_view({
            'get': 'retrieve', 'put': 'update',
            'patch': 'partial_update', 'delete': 'destroy',
        }),
        name='routine-items-detail',
    ),
    # Click event logging
    path('events/click/', ClickEventCreateView.as_view(), name='click-event'),
]
