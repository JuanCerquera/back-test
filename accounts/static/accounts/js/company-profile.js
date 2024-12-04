document.addEventListener('DOMContentLoaded', function () {
    tinymce.init({
        selector: '#id_companyprofile-0-description',
        menubar: false,
        plugins: 'anchor autolink charmap codesample emoticons image link lists media searchreplace table visualblocks wordcount linkchecker',
        //toolbar: 'undo redo | blocks fontfamily fontsize | bold italic underline strikethrough | link image media table mergetags | addcomment showcomments | spellcheckdialog a11ycheck typography | align lineheight | checklist numlist bullist indent outdent | emoticons charmap | removeformat',
        toolbar: 'undo redo | bold italic underline strikethrough | forecolor backcolor | align | checklist numlist bullist indent outdent | emoticons charmap',
    });


    let copyUrlButton = document.querySelector("#copy-url-button")
    copyUrlButton.addEventListener('click', function () {
        let url = document.querySelector("#schedule-url")
        navigator.clipboard.writeText(url.textContent.trim());
        console.log("Copied to clipboard")
    });

});