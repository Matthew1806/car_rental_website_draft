// Mobile hamburger menu toggle
document.addEventListener('DOMContentLoaded', function() {
    const hamburgerMenu = document.getElementById('hamburgerMenu');
    const navMenu = document.getElementById('navMenu');

    if (hamburgerMenu && navMenu) {
        hamburgerMenu.addEventListener('click', function() {
            hamburgerMenu.classList.toggle('active');
            navMenu.classList.toggle('active');
        });

        // Close menu when a link is clicked
        const navLinks = navMenu.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                hamburgerMenu.classList.remove('active');
                navMenu.classList.remove('active');
            });
        });

        // Close menu when clicking outside
        document.addEventListener('click', function(event) {
            const isClickInsideNav = navMenu.contains(event.target);
            const isClickInsideHamburger = hamburgerMenu.contains(event.target);
            
            if (!isClickInsideNav && !isClickInsideHamburger) {
                hamburgerMenu.classList.remove('active');
                navMenu.classList.remove('active');
            }
        });
    }
});

function toggleMenu() {
    const nav = document.querySelector('.navbar nav');
    nav.classList.toggle('show');
    const profileLinks = document.querySelector('.profile-links');
    if (profileLinks) {
        profileLinks.classList.toggle('show');
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

// Dropdown toggle for mobile
document.addEventListener('DOMContentLoaded', function() {
    const dropdowns = document.querySelectorAll('.dropdown-toggle');
    dropdowns.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const menu = this.nextElementSibling;
            menu.classList.toggle('show');
        });
    });
});

// Car functionality
document.addEventListener('DOMContentLoaded', function() {



    // Set minimum date for date inputs to today
    const pickupDateInput = document.getElementById('pickup');
    const returnDateInput = document.getElementById('return_date');
    const carSelect = document.getElementById('car');
    const today = new Date().toISOString().split('T')[0];
    if (pickupDateInput) {
        pickupDateInput.min = today;
    }
    if (returnDateInput) {
        returnDateInput.min = today;
    }

    // Update return date min when pickup date changes
    if (pickupDateInput && returnDateInput) {
        pickupDateInput.addEventListener('change', function() {
            returnDateInput.min = this.value;
            if (returnDateInput.value && returnDateInput.value < this.value) {
                returnDateInput.value = this.value;
            }
        });
    }

    // Disable booked dates for selected car
    // Booking calendar: load Flatpickr dynamically and disable already-booked dates
    (function(){
        if (!carSelect || !pickupDateInput || !returnDateInput) return;

        function loadCSS(href){
            return new Promise((resolve, reject) => {
                if (document.querySelector(`link[href="${href}"]`)) return resolve();
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = href;
                link.onload = resolve;
                link.onerror = reject;
                document.head.appendChild(link);
            });
        }

        function loadScript(src){
            return new Promise((resolve, reject) => {
                if (document.querySelector(`script[src="${src}"]`)) return resolve();
                const s = document.createElement('script');
                s.src = src;
                s.defer = true;
                s.onload = resolve;
                s.onerror = reject;
                document.head.appendChild(s);
            });
        }

        // Initialize flatpickr instances with disabled dates
        let fpPickup = null, fpReturn = null;
        function initPickers(disabledDates){
            try{
                if (fpPickup) fpPickup.destroy();
                if (fpReturn) fpReturn.destroy();
                fpPickup = flatpickr(pickupDateInput, {
                    dateFormat: 'Y-m-d',
                    disable: disabledDates,
                    minDate: 'today',
                    onChange: function(selectedDates, dateStr){
                        if (fpReturn) fpReturn.set('minDate', dateStr || 'today');
                        computeAndShowTotal();
                    }
                });
                fpReturn = flatpickr(returnDateInput, {
                    dateFormat: 'Y-m-d',
                    disable: disabledDates,
                    minDate: pickupDateInput.value || 'today'
                });
            }catch(e){
                console.error('Error initializing flatpickr', e);
            }
        }

        // Compute and display total price in the booking form
        function parsePriceStr(p){
            if(!p) return 0;
            // p may be string like '2000' or '2000.00'
            const n = parseFloat(String(p).replace(/[^0-9.]/g, ''));
            return isNaN(n) ? 0 : n;
        }

        async function computeAndShowTotal(){
            const totalEl = document.getElementById('totalDisplay');
            if(!totalEl) return;
            const opt = carSelect.selectedOptions && carSelect.selectedOptions[0];
            const price = opt ? parsePriceStr(opt.dataset.price) : 0;
            const pickup = pickupDateInput.value;
            const ret = returnDateInput.value;
            if(!price || !pickup || !ret){
                totalEl.textContent = '₱0';
                return;
            }
            try{
                const d1 = new Date(pickup);
                const d2 = new Date(ret);
                let totalDays = Math.round((d2 - d1) / (1000*60*60*24)) + 1;
                if(totalDays < 1) totalDays = 1;
                
                // Fetch approved bookings and exclude overlapping days
                const carId = carSelect.value;
                let chargeDays = totalDays;
                
                if(carId){
                    try{
                        const res = await fetch(`/api/car/${carId}/booked`);
                        if(res.ok){
                            const data = await res.json();
                            const bookedRanges = data.booked_ranges || [];
                            
                            // Count overlapping days
                            const overlappingDays = new Set();
                            bookedRanges.forEach(range => {
                                const rangeStart = new Date(range.from);
                                const rangeEnd = new Date(range.to);
                                
                                // Check if there's overlap
                                if(rangeEnd >= d1 && rangeStart <= d2){
                                    // Calculate overlapping days
                                    let current = new Date(Math.max(d1, rangeStart));
                                    const end = new Date(Math.min(d2, rangeEnd));
                                    
                                    while(current <= end){
                                        overlappingDays.add(current.toISOString().split('T')[0]);
                                        current.setDate(current.getDate() + 1);
                                    }
                                }
                            });
                            
                            // Subtract overlapping days from total
                            chargeDays = totalDays - overlappingDays.size;
                            if(chargeDays < 1) chargeDays = 1;
                        }
                    }catch(err){
                        console.error('Error fetching booked dates', err);
                    }
                }
                
                const total = price * chargeDays;
                // Format with peso symbol
                const formatted = total.toLocaleString('en-PH', { style: 'currency', currency: 'PHP', maximumFractionDigits: 2 });
                totalEl.textContent = formatted;
            }catch(e){
                console.error('Error computing total', e);
                totalEl.textContent = '₱0';
            }
        }

        // Update total when inputs change
        carSelect.addEventListener('change', function(){
            updateForCar();
            computeAndShowTotal();
        });
        pickupDateInput.addEventListener('change', computeAndShowTotal);
        returnDateInput.addEventListener('change', computeAndShowTotal);

        async function fetchBooked(carId){
            if(!carId) return [];
            try{
                const res = await fetch(`/api/car/${carId}/booked`);
                if(!res.ok) return [];
                const data = await res.json();
                // Expecting { booked_ranges: [ {from:'YYYY-MM-DD', to:'YYYY-MM-DD'}, ... ] }
                return data.booked_ranges || [];
            }catch(err){
                console.error('Failed to fetch booked ranges', err);
                return [];
            }
        }

        async function updateForCar(){
            const carId = carSelect.value;
            const booked = await fetchBooked(carId);
            initPickers(booked);
        }

        // Load Flatpickr resources, then initialize
        Promise.all([
            loadCSS('https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css'),
            loadScript('https://cdn.jsdelivr.net/npm/flatpickr')
        ]).then(() => {
            // initialize for current selection
            updateForCar();
            carSelect.addEventListener('change', updateForCar);
        }).catch(err => console.error('Failed to load flatpickr resources', err));
    })();

    // Confirmation page functionality
    const editBookingBtn = document.getElementById('edit-booking-btn');
    const confirmationEditModal = document.getElementById('edit-modal');
    const confirmationCloseModal = document.querySelector('#edit-modal .confirmation-close-modal');
    const confirmationEditForm = document.getElementById('edit-form');

    if (editBookingBtn && confirmationEditModal && confirmationCloseModal && confirmationEditForm) {
        editBookingBtn.addEventListener('click', function() {
            confirmationEditModal.style.display = 'block';
        });

        confirmationCloseModal.addEventListener('click', function() {
            confirmationEditModal.style.display = 'none';
        });

        window.addEventListener('click', function(event) {
            if (event.target === confirmationEditModal) {
                confirmationEditModal.style.display = 'none';
            }
        });

        confirmationEditForm.addEventListener('submit', function(e) {
            e.preventDefault();
            // Here you would send the updated data to the server
            alert('Booking updated successfully!');
            confirmationEditModal.style.display = 'none';
        });
    }

    // Admin toggle functionality
    const toggleButtons = document.querySelectorAll('.toggle-admin-btn');
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.getAttribute('data-user-id');
            const action = this.getAttribute('data-action');
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

            fetch(`/admin/users/${userId}/toggle_admin`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while updating admin status.');
            });
        });
    });

    // Auto-dismiss flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.animation = 'fadeOut 0.3s ease-in forwards';
            setTimeout(() => {
                message.remove();
            }, 300);
        }, 5000);
    });

    // Reviews modal open/close handlers
    const openReviewBtns = document.querySelectorAll('.open-reviews-btn');
    openReviewBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const carId = this.getAttribute('data-car-id');
            const modal = document.getElementById(`reviews-modal-${carId}`);
            if (modal) {
                modal.style.display = 'block';
                modal.setAttribute('aria-hidden', 'false');
            }
        });
    });

    const reviewCloseBtns = document.querySelectorAll('.reviews-modal .close-modal');
    reviewCloseBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const carId = this.getAttribute('data-car-id');
            const modal = document.getElementById(`reviews-modal-${carId}`);
            if (modal) {
                modal.style.display = 'none';
                modal.setAttribute('aria-hidden', 'true');
            }
        });
    });

    window.addEventListener('click', function(event) {
        // close modal when clicking outside modal-content
        if (event.target && event.target.classList && event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
            event.target.setAttribute('aria-hidden', 'true');
        }
    });

});
