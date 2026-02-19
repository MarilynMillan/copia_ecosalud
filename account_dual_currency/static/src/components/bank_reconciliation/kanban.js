/** @odoo-module */
import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(BankRecKanbanController.prototype, {

    // @Override
    getOne2ManyColumns() {
        const data = this.state.bankRecRecordData;
        let lineIdsRecords = data.line_ids.records;
        console.log(lineIdsRecords);
        // Prepare columns.
        let columns = [
            ["account", _t("Account")],
            ["partner", _t("Partner")],
            ["date", _t("Date")],
        ];
        if(lineIdsRecords.some((x) => Boolean(Object.keys(x.data.analytic_distribution).length))){
            columns.push(["analytic_distribution", _t("Analytic")]);
        }
        if(lineIdsRecords.some((x) => x.data.tax_ids.records.length)){
            columns.push(["taxes", _t("Taxes")]);
        }
        if(lineIdsRecords.some((x) => x.data.currency_id[0] !== data.company_currency_id[0])){
            columns.push(["amount_currency", _t("Amount in Currency")], ["currency", _t("Currency")]);
        }
        columns.push(
            ["debit", _t("Debit")],
            ["credit", _t("Credit")],
            ["debit_usd", "Débito $"],
            ["credit_usd", "Crédito $"],
            ["__trash", ""],
        );

        return columns;
    }
});