/**
 * Google Maps Location Picker for Donations
 * Handles location selection with proper synchronization between search and map
 */

class DonationLocationPicker {
    constructor(apiKey, mapContainerId, autocompleteInputId, latitudeInputId, longitudeInputId) {
        this.apiKey = apiKey;
        this.mapContainerId = mapContainerId;
        this.autocompleteInputId = autocompleteInputId;
        this.latitudeInputId = latitudeInputId;
        this.longitudeInputId = longitudeInputId;
        
        this.map = null;
        this.marker = null;
        this.autocomplete = null;
        this.geocoder = null;
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
                    <div style="font-size: 2rem; margin-bottom: 10px;">🗺️</div>
                    <p>Google Maps integration not configured</p>
                </div>
            `;
        }
    }
    
    loadGoogleMaps() {
        const script = document.createElement('script');
        script.src = `https://maps.googleapis.com/maps/api/js?key=${this.apiKey}&libraries=places&callback=initDonationLocationPicker`;
        script.async = true;
        script.defer = true;
        window.initDonationLocationPicker = () => this.initMap();
        document.head.appendChild(script);
    }
    
    initMap() {
        if (typeof google === 'undefined') {
            console.log('Google Maps API not loaded');
            return;
        }
        
        // Get default location from existing values or use Tel Aviv as default
        const latValue = document.getElementById(this.latitudeInputId).value;
        const lngValue = document.getElementById(this.longitudeInputId).value;
        const defaultLoc = { 
            lat: latValue ? parseFloat(latValue) : 32.0853, 
            lng: lngValue ? parseFloat(lngValue) : 34.7818 
        };
        
        console.log("Initializing map with location:", defaultLoc);
        
        this.map = new google.maps.Map(document.getElementById(this.mapContainerId), {
            center: defaultLoc,
            zoom: 12,
            mapTypeControl: true,
            mapTypeControlOptions: {
                style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
                position: google.maps.ControlPosition.TOP_CENTER,
            },
            zoomControl: true,
            streetViewControl: true,
            fullscreenControl: true
        });
        
        // Create marker
        this.marker = new google.maps.Marker({ 
            map: this.map, 
            position: defaultLoc, 
            draggable: true,
            title: "Item Location"
        });
        
        this.geocoder = new google.maps.Geocoder();
        this.setupAutocomplete();
        this.setupMapListeners();
        this.setupMarkerListeners();
        
        // Update location fields with default position
        this.updateLocationFields(defaultLoc);
        
        // If we have coordinates but no address, reverse geocode to get the address
        if (latValue && lngValue && !document.getElementById(this.autocompleteInputId).value) {
            this.reverseGeocode(defaultLoc);
        }
    }
    
    setupAutocomplete() {
        const autocompleteInput = document.getElementById(this.autocompleteInputId);
        if (!autocompleteInput) {
            console.log("Autocomplete input not found:", this.autocompleteInputId);
            return;
        }
        
        console.log("Setting up autocomplete for input:", this.autocompleteInputId);
        
        this.autocomplete = new google.maps.places.Autocomplete(autocompleteInput, {
            fields: ["formatted_address", "geometry", "name"],
            types: ["establishment", "geocode"]
        });
        this.autocomplete.bindTo("bounds", this.map);
        
        // Handle autocomplete selection
        this.autocomplete.addListener('place_changed', () => {
            const place = this.autocomplete.getPlace();
            if (!place.geometry) {
                console.log("No details available for input: '" + place.name + "'");
                return;
            }
            
            console.log("Place selected from autocomplete:", place.formatted_address);
            
            // Update map and marker
            this.map.setCenter(place.geometry.location);
            this.map.setZoom(15);
            this.marker.setPosition(place.geometry.location);
            
            // Update coordinates
            this.updateLocationFields(place.geometry.location);
        });
        
        // Handle manual typing and search
        autocompleteInput.addEventListener('input', () => {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                const query = autocompleteInput.value.trim();
                if (query.length > 2) {
                    console.log("Performing search for:", query);
                    this.performLocationSearch(query);
                }
            }, 500);
        });
        
        // Handle Enter key
        autocompleteInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                const query = autocompleteInput.value.trim();
                if (query) {
                    console.log("Enter key pressed, searching for:", query);
                    this.performLocationSearch(query);
                }
            }
        });
    }
    
    setupMapListeners() {
        // Handle map clicks
        this.map.addListener('click', (event) => {
            console.log("Map clicked at:", event.latLng.lat(), event.latLng.lng());
            this.marker.setPosition(event.latLng);
            this.updateLocationFields(event.latLng);
            this.reverseGeocode(event.latLng);
        });
    }
    
    setupMarkerListeners() {
        // Handle marker drag
        this.marker.addListener('dragend', () => {
            const position = this.marker.getPosition();
            console.log("Marker dragged to:", position.lat(), position.lng());
            this.updateLocationFields(position);
            this.reverseGeocode(position);
        });
    }
    
    performLocationSearch(query) {
        console.log("Performing location search for:", query);
        this.geocoder.geocode({ address: query }, (results, status) => {
            if (status === 'OK' && results[0]) {
                const location = results[0].geometry.location;
                console.log("Search result:", results[0].formatted_address);
                
                // Update map and marker
                this.map.setCenter(location);
                this.map.setZoom(15);
                this.marker.setPosition(location);
                
                // Update coordinates
                this.updateLocationFields(location);
                
                // Update the input field with the formatted address
                document.getElementById(this.autocompleteInputId).value = results[0].formatted_address;
            } else {
                console.log("Geocoding failed:", status);
            }
        });
    }
    
    reverseGeocode(location) {
        console.log("Performing reverse geocoding for:", location.lat(), location.lng());
        this.geocoder.geocode({ location: location }, (results, status) => {
            if (status === 'OK' && results[0]) {
                console.log("Reverse geocoding result:", results[0].formatted_address);
                document.getElementById(this.autocompleteInputId).value = results[0].formatted_address;
            } else {
                console.log("Reverse geocoding failed:", status);
            }
        });
    }
    
    updateLocationFields(location) {
        const lat = typeof location.lat === 'function' ? location.lat() : location.lat;
        const lng = typeof location.lng === 'function' ? location.lng() : location.lng;
        
        document.getElementById(this.latitudeInputId).value = lat;
        document.getElementById(this.longitudeInputId).value = lng;
        
        console.log("Location fields updated:", lat, lng);
    }
}

// Initialize the location picker when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, checking for donation location picker elements...");
    
    // Check if we're on a page that needs the donation location picker
    const mapElement = document.getElementById('map');
    const autocompleteElement = document.getElementById('map-autocomplete');
    
    console.log("Map element found:", !!mapElement);
    console.log("Autocomplete element found:", !!autocompleteElement);
    
    if (mapElement && autocompleteElement) {
        console.log("Initializing DonationLocationPicker...");
        const apiKey = window.GOOGLE_MAPS_API_KEY || '';
        new DonationLocationPicker(apiKey, 'map', 'map-autocomplete', 'latitude', 'longitude');
    } else {
        console.log("Donation location picker elements not found on this page");
    }
});
