function confirmLogout() {
    return confirm("Are you sure you want to logout?");
}
function adminLogin(event) {

    event.preventDefault();

    let username = document.getElementById("username").value;
    let password = document.getElementById("password").value;

    if (username === "admin" && password === "admin123") {

        window.location.href = "admin-dashboard.html";

    } else {

        document.getElementById("message").innerHTML =
            "Invalid username or password";
    }
}