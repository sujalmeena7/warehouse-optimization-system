import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const KpiCard = ({ title, value, icon: Icon, hint, testId }) => {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Card className="rounded-lg border border-slate-200 bg-white shadow-sm hover:border-slate-300" data-testid={`${testId}-card`}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-sm font-medium text-slate-600" data-testid={`${testId}-title`}>
            {title}
          </CardTitle>
          <Icon className="h-5 w-5 text-orange-500" />
        </CardHeader>
        <CardContent>
          <div className="font-heading text-3xl font-bold text-slate-900" data-testid={`${testId}-value`}>
            {value}
          </div>
          <p className="mt-1 text-sm text-slate-500" data-testid={`${testId}-hint`}>
            {hint}
          </p>
        </CardContent>
      </Card>
    </motion.div>
  );
};
