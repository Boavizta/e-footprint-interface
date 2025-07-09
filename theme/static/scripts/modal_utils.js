// MODAL
document.body.addEventListener("openModalDialog", function(event) {
    let modalElement = document.getElementById(event.detail["modal_id"]);
    let modal = new bootstrap.Modal(modalElement);
    modal.show();
});

function dropModal(id){
    let modalElement = document.getElementById(id);
    let modalInstance = bootstrap.Modal.getInstance(modalElement);
    if (modalInstance) {
        modalInstance.hide();
        modalElement.remove();
    }
    let backdrop = document.querySelector('.modal-backdrop');
    if (backdrop) {
        backdrop.remove();
    }
}

document.addEventListener('show.bs.modal', function(event) {
    document.querySelectorAll('.modal-backdrop').forEach(function(el) {
        el.remove();
    });
});

document.body.addEventListener('htmx:beforeSwap', function(event) {
    document.querySelectorAll('.modal-backdrop').forEach(function(el) {
        el.remove();
    });
});

document.addEventListener('hidden.bs.modal', function(event) {
    document.querySelectorAll('.modal-backdrop').forEach(function(el) {
        el.remove();
    });
});
