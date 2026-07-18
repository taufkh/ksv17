/** @odoo-module **/

document.addEventListener("click", (event) => {
    const trigger = event.target.closest(".o_brownie_bill_link");
    if (!trigger) {
        return;
    }
    const href = trigger.dataset.href;
    if (!href) {
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    window.location.assign(href);
});
