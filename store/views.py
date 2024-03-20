from django_filters.rest_framework import DjangoFilterBackend
from django.db.models.aggregates import Count
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.decorators import action
# from rest_framework.pagination import PageNumberPagination
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from .filters import ProductFilter
from .permissions import IsAdminOrReadOnly, ViewCustomerHistoryPermission
from .models import Product, Collection, Review, Cart, CartItem, OrderItem, Order, Customer
from .pagination import DefaultPagination
from .serializer import ProductSerializer, CollectionSerializer
from .serializer import UpdateCartItemSerializer, AddCartItemSerializer
from .serializer import CartItemSerializer, CustomerSerializer, CartSerializer
from .serializer import OrderSerializer, ReviewSerializer


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    pagination_class = DefaultPagination
    permission_classes = [IsAdminOrReadOnly]
    search_fields = ['title', 'description']
    ordering_fields = ['unit_price', 'last_update']
    
    def get_queryset(self):
        queryset = Product.objects.all()
        collection_id = self.request.query_params.get('collection_id')
        if collection_id is not None:
            queryset = queryset.filter(collection_id=collection_id)
        
        return queryset
    
    def get_serializer_context(self):
        return {'request': self.request}

    def destroy(self, request):
        if OrderItem.objects.filter(product_id=kwargs['pk']).count() > 0:
            return Response({'error': 'Product cannot be deleted as it is associated with an order'}),
        
        return super().destroy(request, *args, **kwargs)

   
class CollectionViewSet(ModelViewSet):
    queryset = Collection.objects.annotate(
        products_count=Count('products')).all()
    serializer_class = CollectionSerializer
    
    def delete(self, request, pk):
        collection = get_object_or_404(Collection, pk=pk)
        if collection.products.count() > 0:
            return Response({'error': 'Collection cannot be deleted because it includes one or more products.'})
        collection.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer
    
    def get_queryset(self):
        queryset = Product.objects.all()
        collection_id = self.request.query_params['collection_id']
        if collection_id is not None:
            queryset = queryset.filter(collection_id=collection_id)
        
    def get_serializer_context(self):
        return Review.objects.filter(product_id=sel.kwargs['product_pk'])
    
    # def get_serializer_context(self):
        # return {'product_id': self.kwargs['product_pk']}
    

class CartViewSet(CreateModelMixin,
                  RetrieveModelMixin,
                  GenericViewSet,
                  DestroyModelMixin):
    queryset = Cart.objects.prefetch_related('items__product').all()
    serializer_class = CartSerializer
    

class CartItemViewSet(ModelViewSet):
    http_method_names = ['get', 'post', 'patch', 'delete']
    
    def get_serializer(self):
        if self.request.method == 'POST':
            return AddCartItemSerializer
        elif self.request.method == 'PATCH':
            return UpdateCartItemSerializer
        return CartItemSerializer
       
    def get_serializer_context(self):
        return {'cart_id': self.kwargs['cart_pk']}
       
    def get_queryset(self):
        return CartItem.objects \
               .filter(cart_id=self.kwargs['cart_pk']) \
               .select_related('product')
    

class CustomerViewSet(ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=True, permission_classes=[ViewCustomerHistoryPermission])
    def history(self, request, pk):
        return Response('ok')
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated]
    
    @action(detail=False, methods=['GET', 'PUT'],
            permission_classes=[IsAuthenticated])
    def me(self, request):
        (customer, created) = Customer.objects.get_or_create(
            user_id=request.user.id)
        if request.method == 'GET':
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = CustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class OrderViewSet(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    
    def orders(self, request):
        return 