function whistle(...args) {
	const formData = new FormData()
	formData.append('args', args)
	fetch('/whistle', { method: 'POST', body: formData })
}

document.cookie = "viewport_dimensions=" + window.outerWidth + 'x' + window.outerHeight + '; path=/;';