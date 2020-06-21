# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor
from ..utils import js_to_json, urljoin
import re

to_test = """
https://eng.lsm.lv/article/features/features/ltv-goes-one-on-one-with-latvian-american-businessman-peteris-aloizs-ragauss.a345730/
https://rus.lsm.lv/statja/analitika/analitika/ltv7-govorit-li-pravdu-premer-o-vozmozhnosti-bankrotstva-latvenergo-iz-za-otmeni-oik.a350889/

#other vid format
https://replay.lsm.lv/lv/ieraksts/ltv/105735/gribas-un-talanta-svetita-marina-rebeka-ltv-dokumentala-filma
#plus subs
https://replay.lsm.lv/lv/ieraksts/ltv/131442/atslegas-ronu-sala-kapec-latvija-tomer-neieguva-ronu-salu

#audio
https://rus.lsm.lv/statja/kultura/istorija/iz-istorii-latgalii-dambe-vdol-daugavi-v-daugavpilse-180-let.a351752/


https://www.lsm.lv/raksts/kultura/izklaide/ko-darit-majas-filmas-un-raidijumus-iesaka-eva-johansone.a351555/
"""

class LSMBaseIE(InfoExtractor):
    _VALID_URL = r'''(?x)
        https?://(?:
            ltv\.lsm\.lv/.*/raksts/.*\.id|
            replay\.lsm\.lv/.*/ieraksts/.*/|
            (?:lr1|lr2|klasika|lr4|pieci|naba)\.lsm\.lv/.*/raksts/.*\.a|
            (?:www\.)?pieci\.lv/.*/raksts/.*\.a|
            (?:www\.)?lsm\.lv/raksts/.*\.a|
            rus\.lsm\.lv/statja/.*\.a|
            eng\.lsm\.lv/article/.*\.a
        )(?P<id>\d+)
    '''
    
    _TESTS = [{
        'url': 'https://ltv.lsm.lv/lv/raksts/12.03.2020-panorama.id182334/',
        'md5': '93606c1ff1af0d8a7d42d51f0dd5f683',
        'info_dict': {
            'id': '182334',
            'ext': 'mp4',
            'title': 'Panorāma',
            'description': 'md5:',
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type (for example int or float)
        }
    }]
    
    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id)
        
        result = {
            'id': video_id,
            'formats': [],
        }
        
        result['title'] = self._og_search_title(webpage)
        result['description'] = self._og_search_description(webpage)
        duration = self._og_search_property('video:duration', webpage, default=None)
        if duration != None:
            result['duration'] = int(duration)
        
        embed_url = self._html_search_regex(r'<iframe[^>]+src="(https?://ltv\.lsm\.lv/\?[^"]+ac=videoembed[^"]+)"', webpage, 'embed_url', default=None)
        if embed_url != None:
            webpage = self._download_webpage(embed_url, video_id, headers={'Referer': url})
            url = embed_url
        
        ### Simple audio player
        
        audio_player_config = self._html_search_regex(r"new\s+LSM\.audio\.songPlayer\s*\((.*?)\);", webpage, 'audio_player_config', flags=re.DOTALL, default=None)
        
        if audio_player_config != None:
            audio_player_json = self._parse_json(js_to_json(audio_player_config.split(',', 1)[1]), video_id)
            
            result['formats'].append({
                'url': audio_player_json['downloadUrl'],
                'vcodec': 'none'
            })
            
            return result
        
        ### Video player 1
        
        video_player_config = self._html_search_regex(r"LTV\.Video\.players\.create\((.*?)\);", webpage, 'video_player_config', flags=re.DOTALL, default=None)
        
        if video_player_config != None:
            video_player_json = self._parse_json(js_to_json(video_player_config.split(',', 1)[1]), video_id)
            
            thumbnail = video_player_json.get('poster')
            if thumbnail != None:
                result['thumbnail'] = urljoin(url, thumbnail)
            
            result['subtitles'] = {}
            for subtitle in video_player_json['player']['clip']['subtitles']:
                if subtitle['srclang'] not in result['subtitles']:
                    result['subtitles'][subtitle['srclang']] = []
                result['subtitles'][subtitle['srclang']].append({
                    'ext': 'vtt',
                    'url': urljoin(url, subtitle['src'])
                })
                
            
            for source in video_player_json['player']['clip']['sources']:
                result['formats'].extend(self._extract_m3u8_formats(source['src'], video_id, ext="mp4"))
            
            return result
        
        ### Video player 2
        
        tv_player_url = self._html_search_regex(r'<iframe[^>]+src="((?:https?:)?//embed\.cloudycdn\.services/.+?)"', webpage, 'tv_player_url', default=None)
        
        if tv_player_url != None:
            tv_player_url = self._proto_relative_url(tv_player_url)
            
            tv_player_webpage = self._download_webpage(tv_player_url, video_id, headers={'Referer': url})
            
            tv_player_config = self._html_search_regex(r'var\s+player_source_config\s+=\s*(\{.*?\});', tv_player_webpage, 'tv_player_config', flags=re.DOTALL)
            tv_player_json = self._parse_json(js_to_json(tv_player_config), video_id)
            
            for source in tv_player_json['sources']:
                source_url = self._proto_relative_url(source['src'])
                result['formats'].extend(self._extract_m3u8_formats(source_url, video_id, ext='mp4', headers={'Referer': tv_player_url}))
            
            thumbnail = tv_player_json.get('poster')
            if thumbnail != None:
                result['thumbnail'] = urljoin(tv_player_url, thumbnail)
            
            self._sort_formats(result['formats'])
            return result
        
        ### Radio player
        
        radio_player_url = self._html_search_regex(r'<iframe[^>]+src="(https?://latvijasradio\.lsm\.lv/[^/]+/embed/\?id=.+?)"', webpage, 'radio_player_url', default=None)
        if radio_player_url != None:
            webpage = self._download_webpage(radio_player_url, video_id)
        
        radio_player_config = self._html_search_regex(r"new\s+LR\.audio\.Player\s*\((.*?)\);", webpage, 'radio_player_config', flags=re.DOTALL, default=None)
        
        if radio_player_config != None:
            radio_player_json = self._parse_json(js_to_json('[%s]' % radio_player_config), video_id)
            
            result['thumbnail'] = radio_player_json[1].get('poster')
            
            for media_type in radio_player_json[2]:
                for media in radio_player_json[2][media_type]:
                    result['duration'] = media.get('duration')
                    for source in media['sources']:
                        # other protocols seem to have issues downloading
                        if source['file'].startswith('http'):
                            if source['file'].endswith('.m3u8'):
                                if media_type == 'audio':
                                    ext = 'mp3'
                                else:
                                    ext = 'mp4'
                                result['formats'].extend(self._extract_m3u8_formats(source['file'], video_id, ext=ext))
                            else:
                                new_format = {
                                    'url': source['file']
                                }
                                
                                if media_type == 'audio':
                                    new_format['vcodec'] = 'none'
                                    new_format['preference'] = 10
                                else:
                                    new_format['preference'] = 20
                                
                                result['formats'].append(new_format)
            
            self._sort_formats(result['formats'])
            return result
        
        # self._sort_formats(result['formats'])
        return result
