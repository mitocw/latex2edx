// Function for making new windows with specified html content
function newWindow(html,eqnstr) {
    var windowRef = window.open("",eqnstr,"height=100,width=400");
    if (windowRef) {
        var d = windowRef.document;
        d.open();
        d.write(html);
        d.close();
    }
}

// Add event listeners to allow edX onload functions to run in addition to our own (specified below)
if (window.addEventListener) { // Mozilla, Netscape, Firefox
    window.addEventListener('load', WindowLoad, false);
} else if (window.attachEvent) { // IE
    window.attachEvent('onload', WindowLoad);
}

// Our own onload function to listen for DOMSubtree modifications to call another javascript function that modifies the feedback "Correct" or "Incorrect" for the justification response section
function WindowLoad(event) {
    process_justifications();
    $("#seq_content").bind("DOMSubtreeModified", function() {
        process_justifications();
    });
}

function process_justifications() {
    var debugs = document.getElementsByClassName("debug");
    for (var i=0; i<debugs.length; i++) {
        if (debugs[i].innerHTML == "incorrect") {
             debugs[i].innerHTML = "provide justification";
        }
        if (debugs[i].innerHTML == "correct") {
            debugs[i].innerHTML = "justification submitted";
        }
    }
}

