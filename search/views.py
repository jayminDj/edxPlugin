""" handle requests for courseware search http requests """
import logging
import json
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from search.api import perform_search, course_discovery_search, course_discovery_filter_fields
from search.views import _process_pagination_values, _process_field_values
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# log appears to be standard name used for logger
log = logging.getLogger(__name__)  # pylint: disable=invalid-name


"""
@api {post} /api-pural/search/course_discovery/ Provides search for course using keywords of course name
@apiGroup searchCourse
@apiName getSearchCourse
@apiSampleRequest http://localhost:8000/api-pural/search/course_discovery

@apiParam {string} page_size size of page in pagination
@apiParam {string} page_index index number of page
@apiParam {string} search_string keyword for search course

@apiSuccess {Number}  took how many seconds the operation took
@apiSuccess {Number}  total how many results were found
@apiSuccess {Decimal}  max_score maximum score from these resutls
@apiSuccess {Object[]}  results json array of result documents
@apiSuccess {Object[]}  facets json array of current organizations,lanuages,course type


@apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "facets": {
            "org": {
                "total": 1,
                "terms": {
                    "PROMACT": 1
                },
                "other": 0
            },
            "modes": {
                "total": 1,
                "terms": {
                    "audit": 1
                },
                "other": 0
            },
            "language": {
                "total": 1,
                "terms": {
                    "en": 1
                },
                "other": 0
            }
        },
        "total": 1,
        "max_score": 1.3164924,
        "took": 6,
        "results": [
                {
                    "_type": "course_info",
                    "score": 1.3164924,
                    "_index": "courseware_index",
                    "_score": 1.3164924,
                    "_id": "course-v1:PROMACT+DP1+2017_T1",
                    "data": {
                        "end": "2020-12-30T23:30:00+00:00",
                        "modes": [
                            "audit"
                        ],
                        "language": "en",
                        "course": "course-v1:PROMACT+DP1+2017_T1",
                        "enrollment_start": "2017-01-01T00:00:00+00:00",
                        "number": "DP1",
                        "content": {
                            "short_description": "A module, encapsulates code and data to implement a particular functionality. has an interface that lets clients to access its functionality in an uniform manner. is easily pluggable with another module that expects its interface. is usually packaged in a single unit so that it can be easily deployed. For example, dapper.net encapsulates database access. It has an API to access its functionality. It is a single file that can plugged in a source tree to be built. The concept of module comes from modular programming paradigm which advocates that software should be composed of separate, interchangeable components called modules by breaking down program functions into modules, each of which accomplishes one function and contains everything necessary to accomplish this.",
                            "overview": " About This Course Include your long course description here. The long course description should contain 150-400 words. This is paragraph 2 of the long course description. Add more paragraphs as needed. Make sure to enclose them in paragraph tags. Requirements Add information about the skills and knowledge students need to take this course. Course Staff Staff Member #1 Biography of instructor/staff member #1 Staff Member #2 Biography of instructor/staff member #2 Frequently Asked Questions What web browser should I use? The Open edX platform works best with current versions of Chrome, Firefox or Safari, or with Internet Explorer version 9 and above. See our list of supported browsers for the most up-to-date information. Question #2 Your answer would be displayed here. ",
                            "video": "",
                            "number": "DP1",
                            "display_name": "Demo Module check"
                        },
                        "start": "2017-05-10T07:00:00+00:00",
                        "image_url": "/asset-v1:PROMACT+DP1+2017_T1+type@asset+block@stock-module.jpg",
                        "enrollment_end": "2017-12-31T00:00:00+00:00",
                        "org": "PROMACT",
                        "effort": "02:00",
                        "id": "course-v1:PROMACT+DP1+2017_T1"
                    }
                }
            ]
        }

"""
class courseDiscovery(APIView):

    """
    Search for courses

    Args:
        request (required) - django request object

    Returns:
        http json response with the following fields
            "took" - how many seconds the operation took
            "total" - how many results were found
            "max_score" - maximum score from these resutls
            "results" - json array of result documents

            or

            "error" - displayable information about an error that occured on the server

    POST Params:
        "search_string" (optional) - text with which to search for courses
        "page_size" (optional)- how many results to return per page (defaults to 20, with maximum cutoff at 100)
        "page_index" (optional) - for which page (zero-indexed) to include results (defaults to 0)
    """

    def post(self, request, course_id=None):

        status_code = 500
        search_term = request.POST.get("search_string", None)

        try:
            size, from_, page = _process_pagination_values(request)
            field_dictionary = _process_field_values(request)

            results = course_discovery_search(
                search_term=search_term,
                size=size,
                from_=from_,
                field_dictionary=field_dictionary,
            )

            status_code = 200

        except ValueError as invalid_err:
            results = {
                "error": unicode(invalid_err)
            }
            log.debug(unicode(invalid_err))

        # Allow for broad exceptions here - this is an entry point from external reference
        except Exception as err:  # pylint: disable=broad-except
            results = {
                "error": ('An error occurred when searching for "{search_string}"').format(search_string=search_term)
            }
            log.exception(
                'Search view exception when searching for %s for user %s: %r',
                search_term,
                request.user.id,
                err
            )

        status_code = 200
        return Response(
            status=status.HTTP_200_OK,
            data=results
        )