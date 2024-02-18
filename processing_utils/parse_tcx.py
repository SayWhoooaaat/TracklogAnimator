
import xml.etree.ElementTree as ET
from datetime import datetime

def parse_tcx(tcx_file_path):
    tree = ET.parse(tcx_file_path)
    root = tree.getroot()

    ns = {'default': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2',
          'ns3': 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'}

    track_points = []

    for trackpoint in root.findall(".//default:Trackpoint", ns):
        timestamp = trackpoint.find("./default:Time", ns).text
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

        latitude = float(trackpoint.find("./default:Position/default:LatitudeDegrees", ns).text)
        longitude = float(trackpoint.find("./default:Position/default:LongitudeDegrees", ns).text)
        
        altitude = float(trackpoint.find("./default:AltitudeMeters", ns).text)
        #distance = float(trackpoint.find("./default:DistanceMeters", ns).text)
        #heart_rate = int(trackpoint.find("./default:HeartRateBpm/default:Value", ns).text)
        speed = float(trackpoint.find("./default:Extensions/ns3:TPX/ns3:Speed", ns).text)
        
        track_points.append([timestamp,latitude,longitude,altitude]) # append speed later

    return track_points

