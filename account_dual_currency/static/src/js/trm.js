/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session"; // Importamos la sesion para sacar el usuario
const { Component, onWillStart, useState, onWillDestroy } = owl;

class BCVRates extends Component {
    setup() {
        super.setup(...arguments);
        // Inicializamos el estado con usuario y tiempo vacio
        this.state = useState({ 
            usd: 0, 
            eur: 0,
            user_name: session.name, // Nombre del usuario logueado
            current_time: ''
        });
        
        this.orm = useService('orm');

        // Logica del Reloj
        this.updateClock(); // Primera ejecucion
        this.interval = setInterval(() => this.updateClock(), 1000); // Actualizar cada segundo

        onWillStart(async () => {
            var company_id = session.company_id;
            var rates = await this.orm.call('res.currency', 'get_bcv_systray_rates', [company_id]);
            this.state.usd = rates.usd_rate;
            this.state.eur = rates.eur_rate;
        });

        // Limpiar el intervalo cuando se destruye el widget para no consumir memoria
        onWillDestroy(() => clearInterval(this.interval));
    }

    updateClock() {
        const now = new Date();
        // Formato dia/mes/año hora:minuto:segundo (Estilo Venezuela)
        this.state.current_time = now.toLocaleString('es-VE', { 
            day: '2-digit', month: '2-digit', year: 'numeric', 
            hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true 
        });
    }
}

BCVRates.template = "bcv_rates_menu"; 
export const bcvRatesItem = { Component: BCVRates };

registry.category("systray").add("BCV_RATES", bcvRatesItem, {sequence: 1});
