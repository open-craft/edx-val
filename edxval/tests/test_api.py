# -*- coding: utf-8 -*-
"""
Tests for the API for Video Abstraction Layer
"""

import mock

from django.test import TestCase
from django.db import DatabaseError
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from rest_framework import status
from ddt import ddt, data, unpack

from edxval.models import Profile, Video, EncodedVideo, CourseVideo
from edxval import api as api
from edxval.api import SortDirection, ValCannotCreateError, VideoSortField
from edxval.serializers import VideoSerializer
from edxval.tests import constants, APIAuthTestCase

@ddt
class CreateVideoTest(TestCase):
    """
    Tests the create_video function in api.py.

    This function requires that a Profile object exist.
    """

    def setUp(self):
        """
        Creation of Profile objects that will be used to test video creation
        """
        api.create_profile(constants.PROFILE_DICT_DESKTOP)
        api.create_profile(constants.PROFILE_DICT_MOBILE)

    def test_create_video(self):
        """
        Tests the creation of a video
        """
        video_data = dict(
            encoded_videos=[
                constants.ENCODED_VIDEO_DICT_FISH_MOBILE
            ],
            **constants.VIDEO_DICT_FISH
        )
        result = api.create_video(video_data)
        videos = Video.objects.all()
        self.assertEqual(len(videos), 1)
        self.assertEqual("super-soaker", result)

    @data(
        constants.VIDEO_DICT_FISH,
        constants.VIDEO_DICT_NEGATIVE_DURATION,
        constants.VIDEO_DICT_INVALID_ID
    )
    def test_create_invalid_video(self, data): # pylint: disable=W0621
        """
        Tests the creation of a video with invalid data
        """
        with self.assertRaises(ValCannotCreateError):
            api.create_video(data)

    def test_invalid_profile(self):
        """
        Tests inputting bad profile type
        """
        video_data = dict(
            encoded_videos=[
                dict(
                    profile=constants.PROFILE_DICT_MOBILE,
                    **constants.ENCODED_VIDEO_DICT_MOBILE
                )
            ],
            **constants.VIDEO_DICT_FISH
        )
        with self.assertRaises(ValidationError):
            api.create_video(video_data)


@ddt
class CreateProfileTest(TestCase):
    """
    Tests the create_profile function in the api.py
    """

    def test_create_profile(self):
        """
        Tests the creation of a profile
        """
        result = api.create_profile(constants.PROFILE_DICT_DESKTOP)
        profiles = list(Profile.objects.all())
        self.assertEqual(len(profiles), 6)
        self.assertEqual(
            profiles[-1].profile_name,
            constants.PROFILE_DICT_DESKTOP.get('profile_name')
        )
        self.assertEqual(len(profiles), 6)
        self.assertEqual("desktop", result)

    @data(
        constants.PROFILE_DICT_NEGATIVE_WIDTH,
        constants.PROFILE_DICT_NEGATIVE_HEIGHT,
        constants.PROFILE_DICT_MISSING_EXTENSION,
        constants.PROFILE_DICT_MANY_INVALID,
        constants.PROFILE_DICT_INVALID_NAME,
    )
    def test_invalid_create_profile(self, data):  # pylint: disable=W0621
        """
        Tests the creation of invalid profile data
        """
        with self.assertRaises(ValCannotCreateError):
            api.create_profile(data)


@ddt
class GetVideoTest(TestCase):
    """
    Tests all get videos functions in api.py
    """

    def setUp(self):
        """
        Creates EncodedVideo objects in database
        """
        Profile.objects.create(**constants.PROFILE_DICT_MOBILE)
        Profile.objects.create(**constants.PROFILE_DICT_DESKTOP)
        video = Video.objects.create(**constants.VIDEO_DICT_FISH)
        EncodedVideo.objects.create(
            video=Video.objects.get(
                edx_video_id=constants.VIDEO_DICT_FISH.get("edx_video_id")
            ),
            profile=Profile.objects.get(profile_name="mobile"),
            **constants.ENCODED_VIDEO_DICT_MOBILE
        )
        EncodedVideo.objects.create(
            video=Video.objects.get(
                edx_video_id=constants.VIDEO_DICT_FISH.get("edx_video_id")
            ),
            profile=Profile.objects.get(profile_name="desktop"),
            **constants.ENCODED_VIDEO_DICT_DESKTOP
        )
        self.course_id = 'test-course'
        CourseVideo.objects.create(video=video, course_id=self.course_id)

    def test_get_video_found(self):
        """
        Tests for successful video request
        """
        self.assertIsNotNone(
            api.get_video_info(
                constants.VIDEO_DICT_FISH.get("edx_video_id")
            )
        )

    def test_get_videos_for_course(self):
        """
        Tests retrieving videos for a course id
        """
        videos = list(api.get_videos_for_course(self.course_id))
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]['edx_video_id'], constants.VIDEO_DICT_FISH['edx_video_id'])
        videos = list(api.get_videos_for_course('unknown'))
        self.assertEqual(len(videos), 0)

    def test_no_such_video(self):
        """
        Tests searching for a video that does not exist
        """

        with self.assertRaises(api.ValVideoNotFoundError):
            api.get_video_info("non_existant-video__")
        with self.assertRaises(api.ValVideoNotFoundError):
            api.get_video_info("")

    def test_unicode_input(self):
        """
        Tests if unicode inputs are handled correctly
        """
        with self.assertRaises(api.ValVideoNotFoundError):
            api.get_video_info(u"๓ﻉѻฝ๓ٱซ")

    @mock.patch.object(VideoSerializer, '__init__')
    def test_force_internal_error(self, mock_init):
        """
        Tests to see if an unknown error will be handled
        """
        mock_init.side_effect = Exception("Mock error")
        with self.assertRaises(api.ValInternalError):
            api.get_video_info(
                constants.VIDEO_DICT_FISH.get("edx_video_id")
            )

    @mock.patch.object(Video, '__init__')
    def test_force_database_error(self, mock_get):
        """
        Tests to see if an database error will be handled
        """
        mock_get.side_effect = DatabaseError("DatabaseError")
        with self.assertRaises(api.ValInternalError):
            api.get_video_info(
                constants.VIDEO_DICT_FISH.get("edx_video_id")
            )

    @data(
        # ('not-a-course', ["mobile"]),
        # ("test-course", ["desktop"]),
        ("test-course", ["desktop", "mobile"])
    )
    @unpack
    def test_get_video_for_course_and_profiles(self, course_id, profiles):
        """tests get_video_info_for_course_and_profiles"""
        response = api.get_video_info_for_course_and_profiles(course_id, profiles)
        print response
        self.assertEqual(1,2)


class GetUrlsForProfileTest(TestCase):
    """
    Tests the get_urls_for_profile(s) function in api.py
    """

    def setUp(self):
        """
        Creates EncodedVideo objects in database
        """
        Profile.objects.create(**constants.PROFILE_DICT_MOBILE)
        Profile.objects.create(**constants.PROFILE_DICT_DESKTOP)
        video = Video.objects.create(**constants.VIDEO_DICT_FISH)
        EncodedVideo.objects.create(
            video=Video.objects.get(
                edx_video_id=constants.VIDEO_DICT_FISH.get("edx_video_id")
            ),
            profile=Profile.objects.get(profile_name="mobile"),
            **constants.ENCODED_VIDEO_DICT_MOBILE
        )
        EncodedVideo.objects.create(
            video=Video.objects.get(
                edx_video_id=constants.VIDEO_DICT_FISH.get("edx_video_id")
            ),
            profile=Profile.objects.get(profile_name="desktop"),
            **constants.ENCODED_VIDEO_DICT_DESKTOP
        )
        self.course_id = 'test-course'
        CourseVideo.objects.create(video=video, course_id=self.course_id)

    def test_get_urls_for_profiles(self):
        """
        Tests when the profiles to the video are found
        """
        profiles = ["mobile", "desktop"]
        edx_video_id = constants.VIDEO_DICT_FISH['edx_video_id']
        urls = api.get_urls_for_profiles(edx_video_id, profiles)
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls["mobile"], u'http://www.meowmix.com')
        self.assertEqual(urls["desktop"], u'http://www.meowmagic.com')

    def test_get_urls_for_profiles_no_video(self):
        """
        Tests when there is no video found.
        """
        urls = api.get_urls_for_profiles("not found", ["mobile"])
        self.assertEqual(urls["mobile"], None)

    def test_get_urls_for_profiles_no_profiles(self):
        """
        Tests when the video is found, but not hte profiles.
        """
        profiles = ["not", "found"]
        edx_video_id = constants.VIDEO_DICT_FISH['edx_video_id']
        urls = api.get_urls_for_profiles(edx_video_id, profiles)
        self.assertEqual(len(urls), 2)
        self.assertEqual(urls["not"], None)
        self.assertEqual(urls["found"], None)

    def test_get_url_for_profile(self):
        """
        Tests get_url_for_profile
        """
        profile = "mobile"
        edx_video_id = constants.VIDEO_DICT_FISH['edx_video_id']
        url = api.get_url_for_profile(edx_video_id, profile)
        self.assertEqual(url, u'http://www.meowmix.com')


class GetVideosForIds(TestCase):
    """
    Tests the get_videos_for_ids function in api.py
    """

    def setUp(self):
        """
        Creates EncodedVideo objects in database
        """
        Profile.objects.create(**constants.PROFILE_DICT_MOBILE)
        Profile.objects.create(**constants.PROFILE_DICT_DESKTOP)
        video = Video.objects.create(**constants.VIDEO_DICT_FISH)
        EncodedVideo.objects.create(
            video=Video.objects.get(
                edx_video_id=constants.VIDEO_DICT_FISH.get("edx_video_id")
            ),
            profile=Profile.objects.get(profile_name="mobile"),
            **constants.ENCODED_VIDEO_DICT_MOBILE
        )
        EncodedVideo.objects.create(
            video=Video.objects.get(
                edx_video_id=constants.VIDEO_DICT_FISH.get("edx_video_id")
            ),
            profile=Profile.objects.get(profile_name="desktop"),
            **constants.ENCODED_VIDEO_DICT_DESKTOP
        )
        self.course_id = 'test-course'
        CourseVideo.objects.create(video=video, course_id=self.course_id)

    def test_get_videos_for_id(self):
        """
        Tests retrieving videos for id
        """
        edx_video_id = constants.VIDEO_DICT_FISH['edx_video_id']
        videos = list(api.get_videos_for_ids([edx_video_id]))
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]['edx_video_id'], edx_video_id)
        videos = list(api.get_videos_for_ids(['unknown']))
        self.assertEqual(len(videos), 0)

    def test_get_videos_for_ids(self):
        """
        Tests retrieving videos for ids
        """
        Video.objects.create(**constants.VIDEO_DICT_DIFFERENT_ID_FISH)
        EncodedVideo.objects.create(
            video=Video.objects.get(
                edx_video_id=constants.VIDEO_DICT_DIFFERENT_ID_FISH.get("edx_video_id")
            ),
            profile=Profile.objects.get(profile_name="mobile"),
            **constants.ENCODED_VIDEO_DICT_MOBILE
        )
        edx_video_id = constants.VIDEO_DICT_FISH['edx_video_id']
        edx_video_id_2 = constants.VIDEO_DICT_DIFFERENT_ID_FISH['edx_video_id']
        videos = list(api.get_videos_for_ids([edx_video_id, edx_video_id_2]))
        self.assertEqual(len(videos), 2)

    def test_get_videos_for_ids_duplicates(self):
        """
        Tests retrieving videos for ids when there are duplicate ids
        """
        edx_video_id = constants.VIDEO_DICT_FISH['edx_video_id']
        videos = list(api.get_videos_for_ids([edx_video_id, edx_video_id]))
        self.assertEqual(len(videos), 1)

    def test_get_videos_for_ids_sort(self):
        fish_id = constants.VIDEO_DICT_FISH["edx_video_id"]
        star_id = constants.VIDEO_DICT_STAR["edx_video_id"]
        other_id = "other-video"
        Video.objects.create(**constants.VIDEO_DICT_STAR)
        # This is made to sort with the other videos differently by each field
        Video.objects.create(
            client_video_id="other video",
            duration=555.0,
            edx_video_id=other_id
        )

        def check_sort(sort_field, expected_ids_for_asc):
            """
            Assert that sorting by given field returns videos in the expected
            order (checking both ascending and descending)
            """
            def check_direction(sort_dir, expected_ids):
                """Assert that the given videos match the expected ids"""
                actual_videos = api.get_videos_for_ids(
                    # Make sure it's not just returning the order given
                    list(reversed(expected_ids)),
                    sort_field,
                    sort_dir
                )
                actual_ids = [video["edx_video_id"] for video in actual_videos]
                self.assertEqual(actual_ids, expected_ids)
            check_direction(SortDirection.asc, expected_ids_for_asc)
            check_direction(
                SortDirection.desc,
                list(reversed(expected_ids_for_asc))
            )

        check_sort(VideoSortField.client_video_id, [fish_id, star_id, other_id])
        check_sort(VideoSortField.edx_video_id, [star_id, other_id, fish_id])
        # Check a field with a tie
        check_sort(VideoSortField.duration, [star_id, fish_id, other_id])


class GetVideoInfoTestWithHttpCalls(APIAuthTestCase):
    """
    Tests for the get_info_video, using the HTTP requests to populate database
    """

    def setUp(self):
        """
        Creates EncodedVideo objects in database with HTTP requests.

        The tests are similar to the GetVideoInfoTest class. This class
        is to test that we have the same results, using a populated
        database via HTTP uploads.
        """
        super(GetVideoInfoTestWithHttpCalls, self).setUp()
        Profile.objects.create(**constants.PROFILE_DICT_MOBILE)
        Profile.objects.create(**constants.PROFILE_DICT_DESKTOP)
        url = reverse('video-list')
        response = self.client.post(
            url, constants.COMPLETE_SET_FISH, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_video_found(self):
        """
        Tests for successful video request
        """
        self.assertIsNotNone(
            api.get_video_info(
                constants.COMPLETE_SET_FISH.get("edx_video_id")
            )
        )

    def test_get_info_queries_for_two_encoded_video(self):
        """
        Tests number of queries for a Video/EncodedVideo(1) pair
        """
        with self.assertNumQueries(8):
            api.get_video_info(constants.COMPLETE_SET_FISH.get("edx_video_id"))

    def test_get_info_queries_for_one_encoded_video(self):
        """
        Tests number of queries for a Video/EncodedVideo(1) pair
        """
        url = reverse('video-list')
        response = self.client.post(
            url, constants.COMPLETE_SET_STAR, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        with self.assertNumQueries(6):
            api.get_video_info(constants.COMPLETE_SET_STAR.get("edx_video_id"))

    def test_get_info_queries_for_only_video(self):
        """
        Tests number of queries for a Video with no Encoded Videopair
        """
        url = reverse('video-list')
        response = self.client.post(
            url, constants.VIDEO_DICT_ZEBRA, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        with self.assertNumQueries(4):
            api.get_video_info(constants.VIDEO_DICT_ZEBRA.get("edx_video_id"))

