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

