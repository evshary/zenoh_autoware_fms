import { MapContainer, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useState, useEffect, useRef } from 'react';
import L from 'leaflet'

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
            <MapContainer
                ref={mapRef}
                style={{height:600}} 
                center={props.center} 
                zoom={18} 
                scrollWheelZoom={true} >
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
        
            </MapContainer>
        )
    }
    
}

export default MapViewer;