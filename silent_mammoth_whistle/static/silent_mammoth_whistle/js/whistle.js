/***
 * Sends a POST request representing a client action - with the args as formData.
 */
function whistle(...args) {
	// If the user defines the global variable whistleClientEventPath in their code, we use that url, otherwise we default to /whistle.
	const _smwUrl = typeof whistleClientEventPath === 'string' ? whistleClientEventPath : '/whistle';
	const formData = new FormData()
	args.forEach(arg => formData.append('args', arg))
	fetch(_smwUrl, { method: 'POST', body: formData })
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