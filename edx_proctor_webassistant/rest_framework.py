from rest_framework.pagination import PageNumberPagination


class PaginationBy25(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
