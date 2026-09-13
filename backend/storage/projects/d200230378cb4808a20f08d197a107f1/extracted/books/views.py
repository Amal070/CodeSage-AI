from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Book

class BookListView(APIView):
    """Lists all available books in the bookstore."""
    def get(self, request):
        books = Book.objects.all()
        data = [{'id': b.id, 'title': b.title, 'author': b.author, 'price': str(b.price)} for b in books]
        return Response(data)
