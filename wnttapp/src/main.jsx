import 'bootstrap/dist/css/bootstrap.min.css'
import ReactDOM from 'react-dom/client'
import './css/index.css'
import App from './App'

if (window.innerHeight > innerWidth) {
    window.alert(
        'This app is not designed for portrait mode. Please rotate your device to landscape mode.'
    )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
