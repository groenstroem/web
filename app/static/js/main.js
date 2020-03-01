function updateGreenestHour() {
    var period = $('#dropdown-toggle-period').data('value');
    var horizon = $('#dropdown-toggle-horizon').data('value');
    $.get("/api/v1/greenest-hour/" + period + "/" + horizon, function(data) {
        $("#current-intensity").text(data["current-intensity"]);
        $("#improvement").text(data["improvement"]);
        $("#best-hour-start").text(data["best-hour-start"]);
        $("#best-hour-end").text(data["best-hour-end"]);
        $("#best-hour-intensity").text(data["best-hour-intensity"]);
    });
}

function updateEmissionIntensity() {
    $.get("/api/v1/current-emission-intensity", function(data) {
        $("#jumbotron").css("background-color", data["intensity-level-bgcolor"]);
        $("#jumbotron").css("color", data["intensity-level-fgcolor"]);
        $("#info-link").css("color", data["intensity-level-fgcolor"]);
        $(".btn-transparent").css('border-color', data["intensity-level-border-color"]);
        $("#intensity-level").text(data["intensity-level"]);
        $("#latest-data").text(data["latest-data"]);
        $("#body").css('visibility', 'visible');
        $(".btn-transparent").css('color', data["intensity-level-fgcolor"]);
        var length = data["forecast-length-hours"];
        if (length <= 12) {
            $("#dropdown-12-hours").html(length + " timer");
            $("#dropdown-24-hours").css('visibility', 'collapse');
        } else if (length < 24) {
            $("#dropdown-24-hours").html(length + " timer");
        }

        var plot_data = data["plot-data"];
        var plot_opt = {"renderer": "canvas", "actions": false};
        vegaEmbed("#vis", plot_data, plot_opt);
    });
}

function updateAll() {
    updateEmissionIntensity();
    updateGreenestHour();
}

$(document).ready(function() {
    updateAll();
    setInterval(updateAll, 5*60*1000);
});

$(window).on('focus', function() { updateAll(); });

$(".dropdown-menu>a").on('click', function() {
    var selText = $(this).text();
    var dropdownToggle = $(this).parent('.dropdown-menu').siblings('.dropdown-toggle')
    dropdownToggle.html(selText);
    dropdownToggle.data('value', $(this).data('value'));
    if (dropdownToggle[0].id == "dropdown-toggle-period") {
        $('#hours').html(selText);
    }
    var period = $('#dropdown-toggle-period').data('value');
    if (period > 1) {
        $('#de-den-upper').html("De");
        $('#de-den-lower').html("de");
    } else {
        $('#de-den-upper').html("Den");
        $('#de-den-lower').html("den");
    }
    updateGreenestHour();
});