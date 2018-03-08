from rest_framework.pagination import PageNumberPagination


class PaginationBy25(PageNumberPagination):
    page_size = 25


class PaginationBy50(PageNumberPagination):
    page_size = 50
