import { useMap, useMapEvents, MapContainer, Polyline, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useState, useEffect, useRef } from 'react';
import L from 'leaflet'
// import { iconPerson } from './icon';

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
    iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
    iconUrl: require('leaflet/dist/images/marker-icon.png'),
    shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
    iconSize:[30, 30]
});


const VehicleMarker = ({pose, text, type}) => {
    if(type === 'current'){
        return pose.valid? (
            <Marker position={pose} icon={L.icon({iconUrl: require('./vehicle-removebg-preview.png'), iconSize:[60, 60]})}>
                <Popup>{text}</Popup>
            </Marker>
        ) : null
    }
    return pose.valid? (
        <Marker position={pose}>
            <Popup>{text}</Popup>
        </Marker>
    ) : null
}

const ShowCoordinates = () => {
    const map = useMap();
  
    useEffect(() => {
      if (!map) return;
      const info = L.DomUtil.create('div', 'legend');
  
      const positon = L.Control.extend({
        options: {
          position: 'bottomleft'
        },
  
        onAdd: function () {
          info.textContent = 'Click on map';
          return info;
        }
      })
  
      map.on('click', (e) => {
        info.textContent = e.latlng;
      })
  
      map.addControl(new positon());
  
    }, [map])
  
  
    return null
  
}

const GetCoordinates = (props) => {
    const map = useMap();

    useEffect(() => {
        if (!map) return;

        map.on('click', (e) => {
          props.action(e.latlng);
        })
    
      }, [map])


    return null

}
  
  


const MapViewer = (props) => {
    const mapRef = useRef();

    const [xmlData, setXmlData] = useState(null);
    const [nodes, setNodes] = useState(null);
    const [ways, setWays] = useState(null);

    const [LoadingFile, setLoadingFile] = useState(true);
    const [LoadingNode, setLoadingNode] = useState(true);
    const [LoadingWay, setLoadingWay] = useState(true);
    

    useEffect(() => {
        const fetchData = async () => {
            console.log(props);
            try {
                await fetch(props.xmlFile)
                    .then(response => response.text())
                    .then(data => {
                        console.log(data);
                        var parser=new DOMParser();
                        var xmlDoc=parser.parseFromString(data,"text/xml");
                        // console.log(xmlDoc);
                        setXmlData(xmlDoc);
                    })
            } catch (error) {
                console.error('Error fetching XML file:', error);
            } finally {
                setLoadingFile(false);
            }
        };
        
        const getNodes = function (xmlDoc) {
            if(!xmlDoc) return;

            var result = {};
            var nodes = xmlDoc.getElementsByTagName("node");
            for (var i = 0; i < nodes.length; i++) {
                var node = nodes[i], id = node.getAttribute("id");
                result[id] = [
                    parseFloat(node.getAttribute('lat')),
                    parseFloat(node.getAttribute('lon'))
                ]
                // console.log(node.getAttribute('lat'), node.getAttribute('lon'));
            };
            setNodes(result);
            setLoadingNode(false);
        }
        
        const getWays = function (xmlDoc, nodes) {
            if(!xmlDoc || !nodes) return;

            var result = [];
            var ways = xmlDoc.getElementsByTagName("way");
            for (var i = 0; i < ways.length; i++) {
                var way = ways[i], nds = way.getElementsByTagName("nd");
                var node_list = new Array(nds.length);
                for (var j = 0; j < nds.length; j++) {
                    node_list[j] = nodes[nds[j].getAttribute("ref")];
                }
                result.push(node_list);
                // console.log(node_list);
            }
            setWays(result);
            setLoadingWay(false);
        }
        
        if(!xmlData) fetchData();
        if(!nodes) getNodes(xmlData);
        if(!ways) getWays(xmlData, nodes)
    }, [xmlData, nodes, ways, props.xmlFile]);


    useEffect(() => {
        if (mapRef.current && ways.length > 0) {
            // Calculate the bounds of all the polylines
            const bounds = calculateBounds(ways);

            // Fit the map view to the calculated bounds
            mapRef.current.fitBounds(bounds);
        }
    }, [ways]);

    // Function to calculate bounds of all polylines
    const calculateBounds = (polylines) => {
        let bounds = [];
        polylines.forEach((polyline) => {
            polyline.forEach((point) => {
                bounds = bounds.concat(L.latLng(point[0], point[1]));
            })
        });

        return bounds;
    };
    
    if(LoadingFile || LoadingNode || LoadingWay) {
        // console.log(LoadingFile, LoadingNode, LoadingWay)
        return (
            <MapContainer style={{height:600}} center={props.center} zoom={1} scrollWheelZoom={true} />
        )
    }
    else {
        console.log('ways', ways);
        return (
            <div className={props.classname}>
                <MapContainer
                    ref={mapRef}
                    style={{height:600}} 
                    center={props.center} 
                    zoom={20} 
                    scrollWheelZoom={true} >
                        {/* <TileLayer
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    /> */}
                        {
                            ways.map( (points) => {
                                    // console.log(points)
                                    return (
                                        <Polyline
                                            color={'red'}
                                            opacity={0.7}
                                            weight={2.5}
                                            positions={points}
                                        ></Polyline>
                                    );
                                }
                            )
                        }
                        <ShowCoordinates />
                        <GetCoordinates action={props.clickAction}/>
                        {
                            props.currentMarker.map( (p) => {
                                    // console.log(points)
                                    return (
                                        <VehicleMarker pose={[p.lat, p.lon]} text={p.scope} type={"current"}/>
                                    );
                                }

                            )
                        }
                        <VehicleMarker pose={props.currentMarker} text={"Ego Position"}/>
                        {/* <VehicleMarker pose={props.initMarker} text={"Initialized Position"}/> */}
                        <VehicleMarker pose={props.goalMarker} text={"Goal Position"} type={"goal"}/>
                </MapContainer>
            </div>
        )
    }
    
}

export default MapViewer;