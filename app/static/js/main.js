function updateGreenestPeriod() {
    // Update all data pertaining to the "greenest period of time"
    var period = $('#dropdown-toggle-period').data('value');
    var horizon = $('#dropdown-toggle-horizon').data('value');
    $.get("/api/v1/greenest-period/" + period + "/" + horizon, function(data) {
        $("#current-intensity").text(data["current-intensity"]);
        $("#improvement").text(data["improvement"]);
        $("#best-hour-start").text(data["best-hour-start"]);
        $("#best-hour-end").text(data["best-hour-end"]);
        $("#best-hour-intensity").text(data["best-hour-intensity"]);
    });
}

function updateEmissionIntensity() {
    // Update the main information about emission intensities, and the corresponding plot.
    $.get("/api/v1/current-emission-intensity", function(data) {
        $("#jumbotron").css("background-color", data["intensity-level-bgcolor"]);
        $("#jumbotron").css("color", data["intensity-level-fgcolor"]);
        $("#info-link").css("color", data["intensity-level-fgcolor"]);
        $(".btn-transparent").css('border-color', data["intensity-level-border-color"]);
        $("#intensity-level").text(data["intensity-level"]);
        $("#latest-data").text(data["latest-data"]);
        $("#body").css('visibility', 'visible');
        $(".btn-transparent").css('color', data["intensity-level-fgcolor"]);
        // A priori, we allow selections of 6, 12, and 24 hours in the horizon dropdown, but if
        // our current forecast is shorter than that, we update the values accordingly. Note that
        // we do not have to update the actual data properties themselves, as the API will simply
        // ignore the fact that the desired horizon might be longer than the available forecast.
        var length = data["forecast-length-hours"];
        var selectedHorizon = $('#dropdown-toggle-horizon').data('value');
        if (length <= 12) {
            var newText = length + " timer";
            $("#dropdown-12-hours").html(newText);
            $("#dropdown-24-hours").css('visibility', 'collapse');
            if (selectedHorizon == 12) {
                $('#dropdown-toggle-horizon').html(newText);
            }
        } else if (length < 24) {
            $("#dropdown-24-hours").html(length + " timer");
            if (selectedHorizon == 24) {
                $('#dropdown-toggle-horizon').html(newText);
            }
        }

        // TODO: Rather than generating the plot from scratch, it would make sense to keep the
        // Vega-Lite specification static, and then simply update its data here.
        var plot_data = data["plot-data"];
        var plot_opt = {"renderer": "canvas", "actions": false};
        vegaEmbed("#vis", plot_data, plot_opt);
    });
}

function updateAll() {
    // Update all dynamic data on the page.
    updateEmissionIntensity();
    updateGreenestPeriod();
}

$(document).ready(function() {
    // Immediately set the page data, and refresh it every five minutes.
    updateAll();
    setInterval(updateAll, 5*60*1000);

    // Determine which "Add to home screen" guides to display based on user agents.
    var ua = navigator.userAgent.toLowerCase();
    var isiOS = !!navigator.platform && /iPad|iPhone|iPod/.test(navigator.platform);
    if (ua.indexOf('firefox') > -1 && ua.indexOf('android') > -1)
        $("#firefox-android-guide").css('display', 'inherit');
    if (ua.indexOf('chrome') > -1 && ua.indexOf('android') > -1)
        $("#chrome-android-guide").css('display', 'inherit');
    if (ua.indexOf('fxios') > -1)
        $("#firefox-ios-guide").css('display', 'inherit');
    if (ua.indexOf('crios') > -1)
        $("#chrome-ios-guide").css('display', 'inherit');
    if (ua.indexOf('safari') > -1 && isiOS)
        $("#safari-ios-guide").css('display', 'inherit');
});

// Besides updating page data every five minutes, we also update it on the window 'focus' event. This
// is necessary to ensure updates when users have added the page to their phone/tablet home screen, in
// which case they might otherwise end up with stale data that can go for up to five minutes without updates.
$(window).on('focus', function() { updateAll(); });

$(".dropdown-menu>a").on('click', function() {
    // Get the text of the selected item and replace the dropdown contents with it.
    var selText = $(this).text();
    var dropdownToggle = $(this).parent('.dropdown-menu').siblings('.dropdown-toggle')
    dropdownToggle.html(selText);
    if (dropdownToggle[0].id == "dropdown-toggle-period") {
        $('#hours').html(selText);
    }
    // We use data properties to keep track of the value of the selected item. This allows us to perform
    // the actual update without relying on view-specific properties. If we get much more of this sort of
    // logic, jumping to a more heavy-weight JavaScript framework will make sense.
    dropdownToggle.data('value', $(this).data('value'));
    // Update the grammar on the web page; if we go from 1 hour to 2 hours, we want "den grønneste time" to
    // become "de grønneste timer".
    var period = $('#dropdown-toggle-period').data('value');
    if (period > 1) {
        $('#de-den-upper').html("De");
        $('#de-den-lower').html("de");
    } else {
        $('#de-den-upper').html("Den");
        $('#de-den-lower').html("den");
    }
    updateGreenestPeriod();
});