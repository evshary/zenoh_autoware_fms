$(document).ready(function() {
    const api_server = "http://127.0.0.1:8000/"
    $.ajax({
        type: "GET",
        url: api_server,
        dataType: "json",
        success: function(data) {
            console.log(data);
            document.getElementById("mycontent").innerHTML = data.message;
        },
        error: function(error) {
            console.log(error);
        },
    });
});
