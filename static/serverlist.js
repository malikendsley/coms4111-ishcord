// retrieve the server list from the server
async function getServerList() {
    var uid = document.cookie.split('; ').find(row => row.startsWith('uid=')).split('=')[1];
    //console.log("uid: " + uid);
    await fetch("/api/" + uid + "/servers")
        .then(response => response.json())
        .then(data => {
            console.log("Servers:", data);
            // for each server, create a new div with the details of the server
            // and append it to the div with id "serverlist"
            for (let i = 0; i < data.length; i++) {
                var server = data[i];
                var serverDiv = document.createElement("div");
                serverDiv.className = "server-entry";
                serverDiv.id = "server-" + server.fid;
                serverDiv.innerHTML = "<h2>" + server.name + "</h2><p>" + server.description + "</p>";
                document.getElementById("serverlist").appendChild(serverDiv);
            }
            // create a new div that when clicked, will redirect to dashboard with the server id in the url
            var serverEntries = document.getElementsByClassName("server-entry");
            for (let i = 0; i < serverEntries.length; i++) {
                serverEntries[i].addEventListener("click", function () {
                    window.location.href = "/dashboard/" + data[i].fid + "/general";
                })
            }

            var server = document.cookie.split('; ').find(row => row.startsWith('server=')).split('=')[1];
            console.log("looking for server-" + server);
            var selectedServer = document.getElementById("server-" + server);
            if (selectedServer != null) {
                selectedServer.className = "server-entry selected";
            }
            else {
                console.log("server not found");
            }
        });
}

function updateServer() {
    // get the server id from cookie
    // find the server div with the matching 
}

getServerList();