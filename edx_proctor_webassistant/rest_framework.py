from rest_framework.pagination import PageNumberPagination


class PaginationBy25(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'


class PaginationBy50(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
