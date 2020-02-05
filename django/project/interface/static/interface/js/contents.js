$(document).ready(function () {

    $('#file').on('change', function(){
        var fullPath = document.getElementById('file').value;
        console.log(fullPath);
        console.log(fullPath.split('.').pop());
        var filename = fullPath.split('\\').pop();
        var fileExtension = fullPath.split('.').pop();

        if (fileExtension == 'pdf') {
            $('#pdf-preview').attr('href', filename);
        } else {
            var reader = new FileReader();
                reader.onload = function()
                {
                    var output = document.getElementById('output_image');
                    output.src = reader.result;
                }
                reader.readAsDataURL(event.target.files[0]);
        }
    });
});