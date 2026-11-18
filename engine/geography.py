"""High precision country-mention geotagging; never infer location from publisher."""
import re
# Point is a label anchor, NOT event coordinates. Do not imply street/city precision.
COUNTRIES={
 'portugal':('Portugal',-8.0,39.5),'japan':('Japan',138.0,37.0),
 'brazil':('Brazil',-52.0,-12.0),'australia':('Australia',134.0,-25.0),
 'united kingdom':('United Kingdom',-2.0,54.0),'united states':('United States',-98.0,39.0),
 'france':('France',2.0,47.0),'germany':('Germany',10.0,51.0),
 'china':('China',104.0,35.0),'india':('India',79.0,22.0),
 'canada':('Canada',-106.0,57.0),'south africa':('South Africa',25.0,-29.0),
 'singapore':('Singapore',103.8,1.3),'mexico':('Mexico',-102.0,24.0),
 'argentina':('Argentina',-64.0,-35.0),'russia':('Russia',94.0,61.0),
 'ukraine':('Ukraine',32.0,49.0),'iran':('Iran',54.0,32.0),
 'israel':('Israel',35.0,31.0),'indonesia':('Indonesia',118.0,-2.0),
 'espanha':('Spain',-4.0,40.0),'espana':('Spain',-4.0,40.0),
 'franca':('France',2.0,47.0),'alemanha':('Germany',10.0,51.0),
 'brasil':('Brazil',-52.0,-12.0),'japao':('Japan',138.0,37.0),
 'portugal':('Portugal',-8.0,39.5),
}
def locate(title):
    s=' '.join(re.findall(r'\w+',str(title).casefold()))
    found={v[0]:v for key,v in COUNTRIES.items() if re.search(r'(?<!\w)'+re.escape(key)+r'(?!\w)',s)}
    if len(found)!=1:return None
    name,lon,lat=next(iter(found.values()))
    return {'country':name,'coordinates':[lon,lat], 'precision':'country_label_anchor', 'method':'explicit_country_name_in_headline', 'verified_event_location':False}
