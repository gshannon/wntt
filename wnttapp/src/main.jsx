import 'bootstrap/dist/css/bootstrap.min.css'
import ReactDOM from 'react-dom/client'
import './css/index.css'
import App from './App'

if (window.innerHeight > innerWidth) {
    window.alert(
        'If possible, please rotate your device to landscape mode for optimal presentation.'
    )
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />)
