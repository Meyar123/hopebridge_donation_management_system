/**
 * Google Maps Integration for Donation Management System
 * Shared functionality for location picking and geocoding
 */

class GoogleMapsManager {
    constructor(apiKey, mapContainerId, locationInputId, latitudeInputId, longitudeInputId) {
        this.apiKey = apiKey;
        this.mapContainerId = mapContainerId;
        this.locationInputId = locationInputId;
        this.latitudeInputId = latitudeInputId;
        this.longitudeInputId = longitudeInputId;
        
        this.map = null;
        this.marker = null;
        this.geocoder = null;
        this.autocomplete = null;
        this.searchTimeout = null;
        
        this.init();
    }
    
    init() {
        if (this.apiKey === 'YOUR_API_KEY') {
            this.showPlaceholder();
            return;
        }
        
        this.loadGoogleMaps();
    }
    
    showPlaceholder() {
        const mapDiv = document.getElementById(this.mapContainerId);
        if (mapDiv) {
            mapDiv.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; background: #f8f9fa; color: #666; text-align: center; padding: 20px;">
                    <div style="font-size: 3rem; margin-bottom: 20px;">🗺️</div>
                    <h3 style="margin-bottom: 10px; color: #333;">Google Maps Integration</h3>
                    <p style="margin-bottom: 15px;">To enable the interactive map, you need to:</p>
                    <ol style="text-align: left; margin-bottom: 20px; max-width: 400px;">
                        <li>Get a Google Maps API key from <a href="https://console.cloud.google.com/" target="_blank" style="color: #28a745;">Google Cloud Console</a></li>
                        <li>Enable Maps JavaScript API, Places API, and Geocoding API</li>
                        <li>Replace 'YOUR_API_KEY' in the template with your actual key</li>
                    </ol>
                    <div style="background: #e7f3ff; padding: 15px; border-radius: 5px; border-left: 4px solid #28a745; margin-top: 10px;">
                        <strong>For now:</strong> You can still create activities by typing the location manually. 
                        The coordinates will be set to 0,0 until you configure the API key.
                    </div>
                </div>
            `;
        }
    }
    
    loadGoogleMaps() {
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${this.apiKey}&libraries=places&callback=initGoogleMaps`;
        script.async = true;
        script.defer = true;
        window.initGoogleMaps = () => this.initMap();
        document.head.appendChild(script);
    }
    
    initMap() {
        if (typeof google === 'undefined') {
            console.log('Google Maps API not loaded - API key not configured');
            return;
        }
        
        const defaultLocation = { lat: 32.0853, lng: 34.7818 };
        
        this.map = new google.maps.Map(document.getElementById(this.mapContainerId), {
            zoom: 13,
            center: defaultLocation,
        });

        this.geocoder = new google.maps.Geocoder();
        
        // Test geocoding on initialization
        this.testGeocoding(defaultLocation);
        
        this.setupLocationInput();
        this.setupMapListeners();
        this.setupButtons();
    }
    
    testGeocoding(location) {
        console.log("Testing geocoding...");
        this.geocoder.geocode({ location: location }, (results, status) => {
            console.log("Initial geocoding test status:", status);
            if (status === "OK" && results[0]) {
                console.log("Geocoding is working! Sample result:", results[0].formatted_address);
            } else {
                console.log("Geocoding test failed:", status);
            }
        });
    }
    
    setupLocationInput() {
        const locationInput = document.getElementById(this.locationInputId);
        if (!locationInput) return;
        
        this.autocomplete = new google.maps.places.Autocomplete(locationInput, {
            fields: ["formatted_address", "geometry", "name"],
            types: ["establishment", "geocode"]
        });
        this.autocomplete.bindTo("bounds", this.map);
        
        // Autocomplete selection
        this.autocomplete.addListener("place_changed", () => {
            const place = this.autocomplete.getPlace();
            if (place.geometry) {
                this.map.setCenter(place.geometry.location);
                this.map.setZoom(15);
                this.placeMarker(place.geometry.location);
                this.updateLocationFields(place.geometry.location);
                console.log("Location selected from autocomplete:", place.formatted_address);
            }
        });
        
        // Enter key search
        locationInput.addEventListener("keypress", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                this.performLocationSearch();
            }
        });
        
        // Debounced search as user types
        locationInput.addEventListener("input", () => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                const query = locationInput.value.trim();
                if (query.length > 3) {
                    this.performLocationSearch();
                }
            }, 1000);
        });
    }
    
    setupMapListeners() {
        // Map click listener
        this.map.addListener("click", (event) => {
            this.placeMarker(event.latLng);
            this.updateLocationFields(event.latLng);
            this.reverseGeocode(event.latLng);
        });
    }
    
    setupButtons() {
        // Search button
        const searchBtn = document.getElementById("search-location");
        if (searchBtn) {
            searchBtn.addEventListener("click", () => this.performLocationSearch());
        }
        
        // Current location button
        const currentLocationBtn = document.getElementById("get-current-location");
        if (currentLocationBtn) {
            currentLocationBtn.addEventListener("click", () => this.getCurrentLocation());
        }
        
        // Clear location button
        const clearBtn = document.getElementById("clear-location");
        if (clearBtn) {
            clearBtn.addEventListener("click", () => this.clearLocation());
        }
    }
    
    performLocationSearch() {
        const locationInput = document.getElementById(this.locationInputId);
        const query = locationInput.value.trim();
        if (query) {
            console.log("Performing location search for:", query);
            this.geocoder.geocode({ address: query }, (results, status) => {
                if (status === "OK" && results[0]) {
                    const location = results[0].geometry.location;
                    this.map.setCenter(location);
                    this.map.setZoom(15);
                    this.placeMarker(location);
                    this.updateLocationFields(location);
                    console.log("Location search result:", results[0].formatted_address);
                } else {
                    console.log("Location search failed:", status);
                }
            });
        }
    }
    
    getCurrentLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const pos = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude,
                    };
                    this.map.setCenter(pos);
                    this.map.setZoom(15);
                    this.placeMarker(pos);
                    this.updateLocationFields(pos);
                    this.reverseGeocode(pos);
                },
                () => {
                    alert("Error: The Geolocation service failed.");
                }
            );
        } else {
            alert("Error: Your browser doesn't support geolocation.");
        }
    }
    
    clearLocation() {
        if (this.marker) {
            this.marker.setMap(null);
            this.marker = null;
        }
        document.getElementById(this.latitudeInputId).value = "";
        document.getElementById(this.longitudeInputId).value = "";
        document.getElementById(this.locationInputId).value = "";
    }
    
    placeMarker(location) {
        if (this.marker) {
            this.marker.setMap(null);
        }
        
        this.marker = new google.maps.Marker({
            position: location,
            map: this.map,
            draggable: true,
            title: "Activity Location"
        });

        // Update coordinates when marker is dragged
        this.marker.addListener("dragend", () => {
            this.updateLocationFields(this.marker.getPosition());
            this.reverseGeocode(this.marker.getPosition());
        });
    }
    
    updateLocationFields(location) {
        document.getElementById(this.latitudeInputId).value = location.lat();
        document.getElementById(this.longitudeInputId).value = location.lng();
    }
    
    reverseGeocode(location) {
        this.geocoder.geocode({ location: location }, (results, status) => {
            console.log("Geocoding status:", status);
            if (status === "OK" && results[0]) {
                document.getElementById(this.locationInputId).value = results[0].formatted_address;
                console.log("Location updated:", results[0].formatted_address);
            } else {
                console.log("Geocoding failed:", status);
            }
        });
    }
}

// Initialize Google Maps when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page that needs Google Maps
    if (document.getElementById('map') && document.getElementById('location')) {
        const apiKey = window.GOOGLE_MAPS_API_KEY || '';
        new GoogleMapsManager(apiKey, 'map', 'location', 'latitude', 'longitude');
    }
});
