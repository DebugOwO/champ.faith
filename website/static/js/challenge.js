// written by debuglog#0028
// if you have any questions feel free to ask me :)

function showAlert(message, category) {
    const alertCategoryIndex = {
        1: "info",
        2: "success",
        3: "warning",
        4: "danger"
    };
    const alertBox = document.getElementById("status");
    category = (alertCategoryIndex[category] || "info");
    alertBox.className = `text-${category}`;
    alertBox.innerText = message;
}

function restart() {
    window.top.location = window.top.location;
}

// captcha functions
let enforcement = null;
function assignObject(data) {
    enforcement = data;
}

async function getPublicKey(index) {
    const publicKeyIndex = {
        1: "ACTION_TYPE_ASSET_COMMENT",
        2: "ACTION_TYPE_CLOTHING_ASSET_UPLOAD",
        3: "ACTION_TYPE_FOLLOW_USER",
        4: "ACTION_TYPE_GROUP_JOIN",
        5: "ACTION_TYPE_GROUP_WALL_POST",
        6: "ACTION_TYPE_SUPPORT_REQUEST",
        7: "ACTION_TYPE_WEB_GAMECARD_REDEMPTION",
        8: "ACTION_TYPE_WEB_LOGIN",
        9: "ACTION_TYPE_WEB_RESET_PASSWORD",
        10: "ACTION_TYPE_WEB_SIGNUP"
    };
    const url = "https://apis.rbxcdn.com/captcha/v1/metadata";
    let response = await fetch(url);
    if (response.status === 200) {
        let json = await response.json();
        let publicKey = json["funCaptchaPublicKeys"][publicKeyIndex[index]];
        return publicKey;
    } else {
        showAlert(`Couldn't fetch the public key.\nStatus: ${response.status}`, 4);
        return false;
    }
}

async function getCaptchaJob() {
    const url = "/api/captcha/job";
    let response = await fetch(url);
    if (response.status === 200) {
        let json = await response.json();
        let captchaJob = json["job"];
        return captchaJob;
    } else if (response.status === 202 || response.status === 401) {
        let json = await response.json();
        let message = json["message"];
        showAlert(message, 3);
        return false;
    } else {
        showAlert(`Couldn't fetch a job.\nStatus: ${response.status}`, 4);
        return false;
    }
}

let captchaId = null;
let completedCaptchas = 0;
async function captchaSolved(captchaToken, hiddenCaptcha) {
    const url = "/api/captcha/submit";
    let data = new URLSearchParams();
    data.set("id", captchaId);
    data.set("token", captchaToken);
    const options = {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: data
    };
    let response = await fetch(url, options);
    const regularStatusArray = [200, 202, 400];
    const statusCategoryIndex = {
        200: 2,
        202: 3,
        400: 3,
    };
    if (regularStatusArray.includes(response.status)) {
        if (response.status === 200 && hiddenCaptcha) {
            showAlert("Valid hidden captcha!", statusCategoryIndex[response.status]);
        } else {
            let json = await response.json();
            let message = json["message"];
            showAlert(message, statusCategoryIndex[response.status]);
        }
        console.log(completedCaptchas)
        if (response.status === 200) {
            if (completedCaptchas < 10) {
                completedCaptchas += 1
                enforcement.reset()
                return setTimeout(showCaptcha, 1*1000);
            } else {
                let captchaJob = await getCaptchaJob();
                if (captchaJob) {
                    let captchaData = captchaJob["data"];
                    captchaId = captchaJob["id"];
                    configCaptcha(captchaData);
                    enforcement.reset() // testing
                    // enforcement.run()
                }
            }
        }
    } else {
        showAlert(`Something went wrong.\nStatus: ${response.status}`, 4);
    }
    // return setTimeout(restart, 10*1000);
}

async function showCaptcha() {
    showAlert("Solve the following captcha")
    enforcement.run()
}

function configCaptcha(captchaData) {
    enforcement.setConfig({
        data: {
            blob: captchaData
        },
        onCompleted: function (response) {
            showAlert("Submitting...", 1);
            captchaSolved(response["token"], response["suppressed"]);
        },  // why is "onCompleted" so slow???
        onShow: showAlert("Solve the following captcha"),
        selector: "#captcha",
        mode: "inline"
    })
}

async function main() {
    let captchaJob = await getCaptchaJob();
    if (captchaJob) {
        let captchaIndex = captchaJob["key"];
        let captchaData = captchaJob["data"];
        captchaId = captchaJob["id"];
        let publicKey = await getPublicKey(captchaIndex);
        if (publicKey) {
            const captchaScript = document.createElement("script");
            document.head.appendChild(captchaScript);
            captchaScript.addEventListener("load", function () {
                configCaptcha(captchaData);
            });
            captchaScript.setAttribute("data-callback", "assignObject");
            captchaScript.src = `https://api.arkoselabs.com/v2/${publicKey}/api.js`;
        }
    }
}

window.addEventListener("load", main);