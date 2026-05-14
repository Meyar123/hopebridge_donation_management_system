/**
 * Google Maps Integration for Address Editing
 * Specialized for user profile address management
 */

class GoogleMapsAddressManager {
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
        script.src = `https://maps.googleapis.com/maps/api/js?key=${this.apiKey}&libraries=places&callback=initGoogleMapsAddress`;
        script.async = true;
        script.defer = true;
        window.initGoogleMapsAddress = () => this.initMap();
        document.head.appendChild(script);
    }
    
    initMap() {
        if (typeof google === 'undefined') {
            console.log('Google Maps API not loaded');
            return;
        }
        
        // Get default location from Django template variables
        const defaultLoc = { 
            lat: parseFloat(document.getElementById(this.latitudeInputId).value) || 32.0853, 
            lng: parseFloat(document.getElementById(this.longitudeInputId).value) || 34.7818 
        };
        
        this.map = new google.maps.Map(document.getElementById(this.mapContainerId), {
            center: defaultLoc,
            zoom: 12
        });
        
        this.marker = new google.maps.Marker({ 
            map: this.map, 
            position: defaultLoc, 
            draggable: true 
        });
        
        this.geocoder = new google.maps.Geocoder();
        this.setupAutocomplete();
        this.setupMarkerListeners();
    }
    
    setupAutocomplete() {
        const autocompleteInput = document.getElementById(this.autocompleteInputId);
        if (!autocompleteInput) return;
        
        this.autocomplete = new google.maps.places.Autocomplete(autocompleteInput);
        this.autocomplete.addListener('place_changed', () => {
            const place = this.autocomplete.getPlace();
            if (!place.geometry) return;
            
            this.map.setCenter(place.geometry.location);
            this.marker.setPosition(place.geometry.location);
            this.fillAddressFields(place);
        });
    }
    
    setupMarkerListeners() {
        this.marker.addListener('dragend', () => {
            const pos = this.marker.getPosition();
            document.getElementById(this.latitudeInputId).value = pos.lat();
            document.getElementById(this.longitudeInputId).value = pos.lng();
            this.reverseGeocode(pos.lat(), pos.lng());
        });
    }
    
    fillAddressFields(place) {
        let street = '', city = '', postal = '', country = '', apartment = '';
        
        for (const comp of place.address_components) {
            if (comp.types.includes('route')) street = comp.long_name;
            if (comp.types.includes('street_number')) street = comp.long_name + ' ' + street;
            if (comp.types.includes('locality')) city = comp.long_name;
            if (comp.types.includes('postal_code')) postal = comp.long_name;
            if (comp.types.includes('country')) country = comp.long_name;
            if (comp.types.includes('subpremise')) apartment = comp.long_name;
        }
        
        // Update address fields
        const streetField = document.getElementById('address_street');
        const cityField = document.getElementById('address_city');
        const postalField = document.getElementById('address_postal_code');
        const countryField = document.getElementById('address_country');
        const apartmentField = document.getElementById('address_apartment');
        
        if (streetField) streetField.value = street;
        if (cityField) cityField.value = city;
        if (postalField) postalField.value = postal;
        if (countryField) countryField.value = country;
        if (apartmentField) apartmentField.value = apartment;
        
        // Update coordinates
        document.getElementById(this.latitudeInputId).value = place.geometry.location.lat();
        document.getElementById(this.longitudeInputId).value = place.geometry.location.lng();
    }
    
    reverseGeocode(lat, lng) {
        this.geocoder.geocode({ location: { lat, lng } }, (results, status) => {
            if (status === 'OK' && results[0]) {
                this.fillAddressFields(results[0]);
            }
        });
    }
}

// Initialize Google Maps Address Manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page that needs address editing
    if (document.getElementById('map') && document.getElementById('map-autocomplete')) {
        const apiKey = window.GOOGLE_MAPS_API_KEY || '';
        new GoogleMapsAddressManager(apiKey, 'map', 'map-autocomplete', 'latitude', 'longitude');
    }
});
