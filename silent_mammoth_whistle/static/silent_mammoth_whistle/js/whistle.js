function whistle(...args) {
	const formData = new FormData()
	formData.append('args', args)
	fetch('/whistle', { method: 'POST', body: formData })
}

document.cookie = "viewport_dimensions=" + window.outerWidth + 'x' + window.outerHeight + '; path=/;';

/***
 * This helps ignore bots when counting whistles. Bots don't seem to stick around long enough to execute a delayed JavaScript call so we make an extra web request after a 3 second delay. We then filter these requests out on the Django side so they're not counted as whistles in a session. SessionStorage is used so the call only happens once per session.
 */
window.addEventListener('DOMContentLoaded', (event) => {
	if (!sessionStorage.getItem('whistleSent')) {
		setTimeout(() => {
			whistle('PING')
			sessionStorage.setItem('whistleSent', 'true')
		}, 3000)
	}
})