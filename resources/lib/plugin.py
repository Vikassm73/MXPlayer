# -*- coding: utf-8 -*-
import logging
import xbmcaddon
from . import kodilogging
from . import kodiutils
from . import settings
import sys

from urllib import urlencode
from urllib import quote
from urlparse import parse_qsl

from datetime import datetime

import xbmcgui
import xbmcplugin
import xbmc
import web_pdb
import requests
import itertools
import operator
import collections
import time
import urlresolver

ADD_ON = xbmcaddon.Addon()
logger = logging.getLogger(ADD_ON.getAddonInfo('id'))
kodilogging.config(logger)

_category_t = collections.namedtuple('Category', ['id', 'title', 'item'])

class MxPlayerPlugin(object):

    MAIN_CATEGORIES = {
        'Main': map(lambda x: _category_t(x[0], x[1], None), (
            ('7694f56f59238654b3a6303885f9166f', 'Web Series'),
            ('feacc8bb9a44e3c86e2236381f6baaf3', 'TV'),
            ('a8ac883f2069d71784f4869e2bfe8340', 'Movies'),
            ('72d9820f7da319cbb789a0f8e4b84e7e', 'Music')
        ))
    }
     # movies - 08f8fce450d1ecf00efa820f611cf57b   
    def __init__(self, plugin_args):
        # Get the plugin url in plugin:// notation.
        self.plugin_url = plugin_args[0]
        # Get the plugin handle as an integer number.
        self.handle = int(plugin_args[1])
        # Parse a URL-encoded paramstring to the dictionary of
        # {<parameter>: <value>} elements
        self.params = dict(parse_qsl(plugin_args[2][1:]))
        self.MainUrl='https://api.mxplay.com/v1/web/'
        # Static data
        self.userid='3369f42b-b2ee-41a2-8cfe-84595a464920'
        self.platform = 'com.mxplay.desktop'
        self.languages = settings.get_languages()
        self.session = requests.Session()

        # Initialise the token.
        #self.token = self.params['token'] if 'token' in self.params else self._get_token()

    def _get_headers(self):
        headers = {
            "Origin": "https://www.mxplayer.in/",
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
            "Accept": "*/*",
            "Referer": "https://www.mxplayer.in/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "ETag": "e6c486f793039c8299886cfcc943872c",
            "Server": "AmazonS3",
            "X-Amz-Cf-Id": "IDsM0D5mTKMqip290NYYsFjkUXDHvg7o93lucYuBhPW2R6yUUJ38xw==",
            "x-amz-version-id": "QAh42F5_lCNbCTHV3fVwqn.Afjm1yWdd"
        }

        return headers
    
    def list_season(self, season_id, season_name):
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, season_name)

        data = self.make_request(self.MainUrl+'detail/collection?type=tvshow&id={}&userid={}&platform={}&content-languages={}'.format(season_id,self.userid,self.platform,self.languages))

        for season in data['tabs'][0]['containers']:
            self.add_directory_item(
                title=season['title'],
                content_id=season['id'],
                description=season.get('description'),
                action='show',
                section_next='first',
                item=season
            )

                    
        #self.add_search_item()

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        #xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.handle)

    def list_show(self, show_id, title, show_next):
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, title)
        
        data = self.make_request(self.MainUrl+'detail/tab/tvshowepisodes?{}&type=season&id={}&userid={}&platform={}&content-languages={}'.format(show_next,show_id,self.userid,self.platform,self.languages))

        for shows in data['items']:
            self.add_video_item(shows)
            
        self.add_next_page_and_search_item(
            item=data, original_title=title, action='show')

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.handle)

    def list_folder(self, folder_id, title, folder_name):
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, folder_name)
        

        data = self.make_request(self.MainUrl+
            'list/{}?{}&userid={}&platform={}&content-languages={}'.format(folder_id,folder_name,self.userid,self.platform,self.languages)
            )        
        
        if not data['items']:
            logger.warn('items data is empty for folder! -- {}'.format(data))
            kodiutils.notification('No items found', 'Check logs for api content!')
            return
        #web_pdb.set_trace()
        for item in data['items']:
            if item['container'] is not None: 
                subtype = item['container'].get('type')
            else: 
                subtype = item.get('type')

            newtitle='{} (Count - {})'.format(item['title'],item.get('videoCount'))
            if subtype in ['folder']:
                self.add_directory_item(
                    content_id=item['id'],
                    title=newtitle,
                    description=item.get('description'),
                    action='folder',
                    section_next=folder_name,
                    item=item
                )

            elif subtype in [
                'trailer', 'movie', 'video',
                'episode', 'teaser', 'music',
                'webisode', 'clip', 'shorts',
                'news','album' , 'season','liveChannel'
            ]:
                self.add_video_item(item)

            elif subtype in ['original', 'tvshow']:
                self.add_directory_item(
                    content_id=item['id'],
                    title=newtitle,
                    description= self.get_description(item),
                    action='season',
                    section_next=folder_name,
                    item=item
                )               #item['publisher'].get('name')
    
            elif subtype not in ['external_link']:
                logger.warn(u'Skipping rendering sub-type from item - {}: {}'.format(subtype, item))
                if settings.is_debug():
                    kodiutils.notification(
                        'Unhandled asset type!',
                        '{}'.format(subtype),
                        icon=xbmcgui.NOTIFICATION_WARNING,
                    )

        self.add_next_page_and_search_item(
            item=data, original_title=folder_name, action='folder'
        )

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.handle)


    def list_sections(self,sec_id, sec_next):
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, 'sections')
        data = self.make_request(self.MainUrl+'home/tab/{}?{}&userid={}&platform={}&content-languages={}'.format(sec_id, sec_next,self.userid,self.platform,self.languages))

        for item in data['sections']:
            self.add_directory_item(
                title=item.get('name'),
                content_id=item.get('id'),
                description=item.get('name'),
                section_next=item.get('next'),
                action='folder'
            )

        
        self.add_next_page_and_search_item(
            item=data, original_title='sections', action='sections')

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.handle)

    @staticmethod
    def get_user_input():
        kb = xbmc.Keyboard('', 'Search for Movies/TV Shows/Trailers/Videos in all languages')
        kb.doModal()  # Onscreen keyboard appears
        if not kb.isConfirmed():
            return

        # User input
        return kb.getText()

    def list_search(self):
        query = MxPlayerPlugin.get_user_input()
        if not query:
            return []

        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, 'Search/{}'.format(query))

        data = self.make_request(self.MainUrl+'search/result?query={}&userid={}&platform={}&content-languages={}'.format(quote(query),self.userid,self.platform,self.languages))
        
        for item in data['sections']:
            
            if item.get('id')in ['shows','album']:
                self.add_directory_item(
                    content_id=item['items'][0].get('id'),
                    title=item['items'][0].get('title'),
                    description= item['items'][0].get('title'),
                    action='season',
                    section_next=item.get('next'),
                    item=item)
            elif item.get('id') in ['shorts','movie','music']:
                if item['items'][0].get('stream') is not None:
                    self.add_video_item(item['items'][0])

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.endOfDirectory(self.handle)

    def make_request(self, url):
        logger.info("Making request: {}".format(url))
        response = self.session.get(url, headers=self._get_headers(), cookies=self.session.cookies)
        assert response.status_code == 200
        return response.json()

    @staticmethod
    def is_url_image(image_url):
       image_formats = ("image/png", "image/jpeg", "image/jpg")
       r = requests.head(image_url)
       if r.headers["content-type"] in image_formats:
          return True
       return False

    @staticmethod
    def get_genre(item):
        """
        Returns a string of genre -- comma separated if multiple genres.
        Returns ALL as default.
        """
        if not item:
            return 'ALL'

        data=item.get('genres')

        return ",".join(data) if data else 'ALL'

    @staticmethod
    def get_description(item):
        """
        Returns video description.
        """
        #web_pdb.set_trace()
        publisher=''
        provider=''
        actor = []
        director=[]
        for items in item['contributors']:
            if items.get('type')=='actor': 
                if items.get('name') is not None:
                    actor.append (items.get('name').encode("utf-8"))
            elif items.get('type')=='director':
                director.append (items.get('name').encode("utf-8"))
        
        myactor = ",".join(actor)
        mydirector = ",".join(director)
        if item['publisher'] is not None:
            publisher=item['publisher'].get('name')
        if item['stream'] is not None:
            provider=item['stream'].get('provider')
        
        
        description='Actor : {} \nDirector : {} \nPublisher : {} \nProvider : {}'.format(myactor,mydirector,publisher,provider)

        return description
    
    @staticmethod
    def get_images(item):
        """
        Returns a tuple of list_image & cover_image.
        """
        #web_pdb.set_trace()  

        if item['image'].get('16x9') is not None: 
            base_images = item['image'].get('16x9')
        else:
            base_images = item['publisher']['image'].get('16x9')
        
        #if item['imageInfo'][0].get('url') is not None: 
        #    base_images = item['imageInfo'][0].get('url')

        if base_images is not None: 
            Segments = base_images.rpartition('/')
            images1='https://j2apps.s.llnwi.net/is1'+Segments[0]+'/16x9/9x/'+Segments[2]
        
        #images2=None

        if item['imageInfo'][1].get('url') is not None: 
            images2 = 'https://isa-1.mxplay.com/'+item['imageInfo'][1].get('url')

        if images2 is None:
            images2=images1
        """
        if base_images[:4]=='http':
            images1=base_images
            images2=item['image'].get('2x3')     
        else:
            images1='https://j2apps.s.llnwi.net/' + base_images
            images2='https://j2apps.s.llnwi.net/' + item['image'].get('2x3')
        
        if not images:
            return None, None
        """
        return images1, images2

    def add_video_item(self, video):
        # Create a list item with a text label and a thumbnail image.

        episode_no = video.get('sequence')
        episode_date = video.get('releaseDate')

        if episode_date:
            try:
                episode_date = datetime(
                    *(time.strptime(episode_date.split('T')[0], "%Y-%m-%d")[0:6])
                )
            except Exception as e:
                logger.warn('Failed to parse the episode date - {} -- {}'.format(episode_date, str(e)))
                episode_date = None
                pass

        if episode_no==0:
            if episode_date:
                title = u'{} | {}'.format(video['title'],episode_date.strftime('%d.%m.%Y'))
            else:
                title = u'{}'.format(video['title']) 
            #title = u'{} | {}'.format(video['title'],episode_date.strftime('%d.%m.%Y') if episode_date else None)   
        else:
            title = u'{} - {} | {}'.format(episode_no, video['title'],episode_date.strftime('%d.%m.%Y') if episode_date else None)
        
               
        type=video['type']
        if video['container'] is not None: 
            VideoType = video['container'].get('type')
        else: 
            VideoType = video.get('type')
                        
        
        videoid=video['id']
        if video['stream']:
            if video['stream'].get('provider')== 'youtube':
                stream_url='https://www.youtube.com/embed/{}?autoplay=1&rel=0&modestbranding=1&playsinline=1&iv_load_policy=3&start=0&enablejsapi=1&origin=https://www.mxplayer.in&widgetid=1'.format(video['stream']['youtube'].get('id'))
                weburl = urlresolver.HostedMediaFile(url=stream_url).resolve()
            elif video['stream']['sony'] is not None: 
            	weburl = video['stream']['sony'].get('hlsUrl')
            elif video['stream']['thirdParty'] is not None: 
            	weburl = video['stream']['thirdParty'].get('hlsUrl')
            elif video['stream']['altBalaji'] is not None: 	
				videoid=video['stream']['altBalaji'].get('dashId') 
				weburl = video['stream']['altBalaji'].get('hlsUrl')
            elif video['stream']['hls'] is not None:
                if  video['stream']['hls'].get('base')  is not None:
                	base_url=video['stream']['hls'].get('base')
                else:
            		base_url=video['stream']['hls'].get('high')
                if base_url[:4]=='http':
                    weburl=base_url          
                else:
                    weburl='https://j2apps.s.llnwi.net/' + base_url
            elif video['stream']['mxplay']['hls'] is not None:
                weburl = video['stream']['mxplay']['hls'].get('main')

        list_item = xbmcgui.ListItem(label=title)

        # Set additional info for the list item.

        description=self.get_description(video)
        
        list_item.setInfo('video', {
            'title': title,
            'genre': MxPlayerPlugin.get_genre(video),
            'episode': episode_no,
            'webUrl': weburl,
            'plot': description,
            'duration': video.get('duration'),
            'year': episode_date.year if episode_date else None,
            'date': episode_date.strftime('%d.%m.%Y') if episode_date else None,
            'mediatype': 'video',
        })

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        if VideoType != 'liveChannel':
	        list_image, cover_image = MxPlayerPlugin.get_images(video)
	        list_item.setArt({
	            'thumb': list_image or cover_image,
	            'icon': list_image or cover_image,
	            'fanart': cover_image or list_image,
	        })

        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        list_item.setProperty('IsPlayable', 'true')

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=play&video=http:
        # //www.vidsplay.com/wp-content/uploads/2017/04/crab.mp4
        url = self.get_url(action='play', content_id=videoid,video_url=weburl ,type=VideoType)

        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, is_folder)
        xbmcplugin.setContent(self.handle, 'videos')

        
    def add_directory_item(
        self,
        title,
        description,
        content_id,
        action,
        section_next,
        item=None,
    ):
        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=title)

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        # In a real-life plugin you need to set each image accordingly.
        if item and item.get('image') is not None:
            cover_image, list_image = MxPlayerPlugin.get_images(item)
            list_item.setArt({
                'poster': list_image or cover_image,
                'thumb': list_image or cover_image,
                'icon': list_image or cover_image,
                'fanart': cover_image or list_image
            })

        #web_pdb.set_trace()

        list_item.setInfo('video', {
            'count': content_id,
            'title': title,
            'genre': self.get_genre(item),
            'plot': description,
            'mediatype': 'tvshow'
        })

        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = self.get_url(
            action=action,
            content_id=content_id,
            section_next=section_next,
            title=title
        )

        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(self.handle, url, list_item, is_folder)

#if item.get('pageDirection', 0) * item.get('limit', 0) < item.get('total', 0):

    def add_next_page_and_search_item(self, item, original_title, action):
       
        if item['next'] is not None:
            title = '| Next Page >>>'
            list_item = xbmcgui.ListItem(label=title)
            list_item.setInfo('video', {
                'mediatype': 'video'
            })
            
            
            if action=='sections':
                url = self.get_url(
                    action=action,
                    content_id=self.params.get('content_id'),
                    section_next=item['next'],
                    title=original_title
                )
            elif action=='folder':
                 url = self.get_url(
                    action=action,
                    content_id=item['id'],
                    section_next=item['next'],
                    title=original_title
                )           
            
            else:
                 url = self.get_url(
                    action=action,
                    content_id=item['id'],
                    section_next=item['next'],
                    title=original_title
                )
                
                #page_number=item['pageDirection'] + 1,
            # is_folder = True means that this item opens a sub-list of lower level items.
            is_folder = True

            # Add our item to the Kodi virtual folder listing.
            xbmcplugin.addDirectoryItem(self.handle, url, list_item, is_folder)

        # Add Search item.
        self.add_search_item()

    def add_search_item(self):
        self.add_directory_item(
            title='| Search', content_id=1, description='Search', action='search',section_next='Search'
        )

    @staticmethod
    def safe_string(content):
        import unicodedata

        if not content:
            return content

        if isinstance(content, unicode):
            content = unicodedata.normalize('NFKD', content).encode('ascii', 'ignore')

        return content

    def get_url(self, **kwargs):
        """
        Create a URL for calling the plugin recursively from the given set of keyword arguments.

        :param kwargs: "argument=value" pairs
        :type kwargs: dict
        :return: plugin call URL
        :rtype: str
        """
        valid_kwargs = {
            key: MxPlayerPlugin.safe_string(value)
            for key, value in kwargs.iteritems()
            if value is not None
        }
        return '{0}?{1}'.format(self.plugin_url, urlencode(valid_kwargs))

        
    def play_video(self, item_id, title, video_url):
        """
        Play a video by the provided path.
        """
        #
        
        if not video_url:
            raise ValueError('Missing video URL for {}'.format(item_id))

        logger.debug('Playing video: {}'.format(video_url))
        # Create a playable item with a path to play.
        
                
        play_item = xbmcgui.ListItem(label=title, path=video_url)

        #header=self._get_headers()
        #licURL='https://api.mxplay.com/v1/drm/balaji/ticket/?&streamId={}'.format(item_id)

        #header="User-Agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
        #header=header+"&content_provider=xstream1"
        #web_pdb.set_trace()

        play_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
        if (video_url.find('mpd') != -1):
        	play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
        else:
        	play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
        play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
        play_item.setMimeType('application/dash+xml')
        play_item.setContentLookup(False)


        #play_item.setProperty('inputstream.adaptive.license_key', licURL)
        #play_item.setProperty("inputstream.adaptive.stream_headers", header)

        # Pass the item to the Kodi player.
        xbmcplugin.setResolvedUrl(self.handle, True, listitem=play_item)     

    def get_video_url(item):

            
        for video in item['items']:
            if video['stream']['sony'] is not None: 
                hls_url = video['stream']['sony'].get('dashUrl')
                break
            elif video['stream']['hls'] is not None:
                base_url = video['stream']['hls'].get('base')
                hls_url ='https://j2apps.s.llnwi.net/' + base_url
                break
            else: 
                continue
                

        return '{url}'.format(url=hls_url)
       


    def list_main(self):
        # Set plugin category. It is displayed in some skins as the name
        # of the current section.
        xbmcplugin.setPluginCategory(self.handle, 'main')

        for category in MxPlayerPlugin.MAIN_CATEGORIES['Main']:
            self.add_directory_item(
                content_id=category[0],
                title=category[1],
                description=category[1],
                action='sections',
                section_next='first',
                item=None
            )

        self.add_search_item()

        # Add a sort method for the virtual folder items (alphabetically, ignore articles)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_NONE)

        # Finish creating a virtual folder.
        xbmcplugin.endOfDirectory(self.handle)
        
    def router(self):
        """
        Main routing function which parses the plugin param string and handles it appropirately.
        """
        # Check the parameters passed to the plugin
        logger.info('Handling route params -- {}'.format(self.params))

        if self.params:
            action = self.params.get('action')
            content_id = self.params.get('content_id')
            title = self.params.get('title')

            section_next=self.params.get('section_next')
            if action == 'sections':
                self.list_sections(content_id, section_next)

            elif action == 'folder':
                self.list_folder(content_id,title,section_next)

            elif action == 'show':
                self.list_show(content_id, title,section_next)

            elif action == 'season':
                self.list_season(content_id, title)

            elif action == 'play':
                self.play_video(content_id,title,self.params.get('video_url'))

            elif action == 'search':
                self.list_search()

            else:
                # If the provided paramstring does not contain a supported action
                # we raise an exception. This helps to catch coding errors,
                # e.g. typos in action names.
                raise ValueError('Invalid paramstring: {0}!'.format(self.params))

        else:
            self.list_main()
            # List all the channels at the base level.
            #self.list_sections('next=075a74a79336b00ebdd74d235badbcf0') next=02ea6f61f67a90c120380f3849f8435e
            #self.list_sections('')
            

def run():
    # Initial stuffs.
    #kodiutils.cleanup_temp_dir()

    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    MxPlayerPlugin(sys.argv).router()
