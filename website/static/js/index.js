function removeLoadingScreen() {
    const loadingBackground = document.getElementById("welcome");
    const avatar = document.getElementById("avatar");
    avatar.onload = function () {
        setTimeout(function () {
            loadingBackground.ontransitionend = function () {
                loadingBackground.remove();
            }
            loadingBackground.classList.add("fade");
        }, 300);
    }
    avatar.src = "/static/images/avatar/2.webp";
}

const video = document.getElementById("video");
function playBackground() {
    document.removeEventListener("click", playBackground);
    removeLoadingScreen();

    let currentVideoTime = sessionStorage.getItem("currentVideoTime");
    video.currentTime = (currentVideoTime || 0);
    video.volume = 0;
    video.play();
    let fadeVolume = setInterval(function () {
        if (video.volume < 0.05) {
            video.volume += 0.0025;
        } else {
            clearInterval(fadeVolume);
        }
    }, 150);

    window.onbeforeunload = function () {
        sessionStorage.setItem("currentVideoTime", video.currentTime);
    };
}

let mobileDeviceSize = window.matchMedia("(max-width: 991px)");
function main() {
    if (mobileDeviceSize.matches) {
        document.addEventListener("click", removeLoadingScreen);
    } else {
        video.setAttribute("preload", "auto");
        document.addEventListener("click", playBackground);
    }
}

window.addEventListener("load", main);