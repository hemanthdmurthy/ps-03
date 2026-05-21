import React, { useState, useEffect, useMemo } from 'react';
import { 
  BarChart3, 
  Zap, 
  DollarSign, 
  Layers, 
  Activity, 
  Search, 
  ChevronDown, 
  ArrowUpRight, 
  ArrowDownRight,
  RefreshCcw,
  Clock,
  Building2,
  Cpu,
  MoreVertical
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip,
  Legend
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Utility for tailwind classes
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const TokenDashboard = () => {
  const [metrics, setMetrics] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchMetrics();
    fetchLogs();
    const interval = setInterval(() => {
      fetchMetrics();
      fetchLogs();
    }, 15000); // Poll every 15s for "real-time" feel
    return () => clearInterval(interval);
  }, []);

  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/tokens/metrics');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setMetrics(data);
    } catch (error) {
      console.error("Error fetching token metrics:", error);
    }
  };

  const fetchLogs = async () => {
    try {
      const response = await fetch('/api/tokens/logs');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setLogs(data);
    } catch (error) {
      console.error("Error fetching token logs:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = useMemo(() => {
    if (!searchQuery) return logs;
    return logs.filter(log => 
      log.company_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.domain_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.model_name?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [logs, searchQuery]);

  // Mock historical data for sparklines
  const generateSparkline = (val) => {
    const base = parseInt(val) || 100;
    return Array.from({ length: 10 }, (_, i) => ({
      value: base + Math.floor(Math.random() * base * 0.2) * (i % 2 === 0 ? 1 : -1)
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-height-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
          <p className="text-slate-400 font-medium animate-pulse">Initializing Intelligence Dashboard...</p>
        </div>
      </div>
    );
  }

  const domainData = Object.entries(metrics?.domain_wise_breakdown || {})
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  const modelData = Object.entries(metrics?.model_wise_breakdown || {})
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  const COLORS = ['#8b5cf6', '#06b6d4', '#2dd4bf', '#f59e0b', '#ef4444', '#ec4899'];

  return (
    <div className="max-w-[1600px] mx-auto p-8 space-y-10 animate-in fade-in duration-1000">
      
      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1">
          <motion.h1 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-5xl font-extrabold tracking-tight text-white"
          >
            AI <span className="text-gradient">Token Intelligence</span>
          </motion.h1>
          <p className="text-slate-400 text-lg max-w-2xl">
            Real-time monitoring of LLM consumption, operational cost, and model performance.
          </p>
        </div>
        
        <div className="flex items-center gap-3 px-4 py-2 rounded-full glass-card border-emerald-500/20">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
          <span className="text-emerald-400 font-semibold text-sm uppercase tracking-wider">System Active</span>
        </div>
      </div>

      {/* Metrics Overview Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          title="Total Tokens" 
          value={metrics?.total_tokens_all_time?.toLocaleString() || '0'} 
          trend="+12.5%" 
          icon={<Zap className="w-5 h-5 text-indigo-400" />}
          data={generateSparkline(metrics?.total_tokens_all_time)}
          color="#8b5cf6"
        />
        <MetricCard 
          title="Estimated Cost" 
          value={`$${metrics?.total_cost_usd?.toFixed(3) || '0.000'}`} 
          trend="+8.2%" 
          icon={<DollarSign className="w-5 h-5 text-emerald-400" />}
          data={generateSparkline((metrics?.total_cost_usd ?? 0) * 10000)}
          color="#10b981"
        />
        <MetricCard 
          title="Avg Tokens / Co" 
          value={metrics?.avg_tokens_per_company?.toLocaleString() || '0'} 
          trend="-2.4%" 
          icon={<Layers className="w-5 h-5 text-cyan-400" />}
          data={generateSparkline(metrics?.avg_tokens_per_company)}
          color="#06b6d4"
        />
        <MetricCard 
          title="Total Requests" 
          value={metrics?.total_requests || '0'} 
          trend="+15.1%" 
          icon={<Activity className="w-5 h-5 text-violet-400" />}
          data={generateSparkline(metrics?.total_requests)}
          color="#a855f7"
        />
      </div>

      {/* Analytics Visualization Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Domain Usage Breakdown */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="lg:col-span-1 glass-card rounded-3xl p-8 border-white/5"
        >
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
              Domain Usage Breakdown
            </h2>
            <MoreVertical className="w-5 h-5 text-slate-500 cursor-pointer" />
          </div>
          
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={domainData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  animationBegin={0}
                  animationDuration={1500}
                >
                  {domainData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(15, 23, 42, 0.9)', 
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '12px',
                    color: '#fff'
                  }}
                  itemStyle={{ color: '#fff' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          
          <div className="mt-6 space-y-3">
            {domainData.slice(0, 4).map((item, index) => (
              <div key={item.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[index] }} />
                  <span className="text-slate-400 text-sm font-medium">{item.name}</span>
                </div>
                <span className="text-white text-sm font-bold">
                  {Math.round((item.value / (metrics?.total_tokens_all_time || 1)) * 100)}%
                </span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Model Distribution */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-2 glass-card rounded-3xl p-8 border-white/5"
        >
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-500" />
              Model Distribution
            </h2>
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">
              <RefreshCcw className="w-3 h-3" />
              AUTO-SYNCING
            </div>
          </div>
          
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelData} layout="vertical" margin={{ left: 20, right: 30 }}>
                <XAxis type="number" hide />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fill: '#94a3b8', fontSize: 12, fontWeight: 600 }}
                  width={100}
                />
                <Tooltip 
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  contentStyle={{ 
                    backgroundColor: 'rgba(15, 23, 42, 0.9)', 
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '12px',
                    color: '#fff'
                  }}
                />
                <Bar 
                  dataKey="value" 
                  radius={[0, 4, 4, 0]} 
                  barSize={20}
                  animationDuration={1500}
                >
                  {modelData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={`url(#barGradient-${index})`} />
                  ))}
                </Bar>
                <defs>
                  {modelData.map((_, i) => (
                    <linearGradient key={i} id={`barGradient-${i}`} x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.8} />
                      <stop offset="100%" stopColor={COLORS[i % COLORS.length]} stopOpacity={0.4} />
                    </linearGradient>
                  ))}
                </defs>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Real-time Token Trace Table */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass-card rounded-3xl overflow-hidden border-white/5"
      >
        <div className="p-8 border-b border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">Live Token Trace</h2>
            <p className="text-slate-400 text-sm">Granular execution logs for all AI orchestrations.</p>
          </div>
          
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500 group-focus-within:text-indigo-400 transition-colors" />
            <input 
              type="text" 
              placeholder="Search companies, domains, models..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-slate-900/50 border border-white/5 rounded-2xl py-3 pl-12 pr-6 text-sm text-white w-full md:w-[400px] outline-none focus:border-indigo-500/50 focus:ring-4 focus:ring-indigo-500/10 transition-all"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-white/[0.02]">
                <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5">
                  <div className="flex items-center gap-2">Timestamp <ChevronDown className="w-3 h-3" /></div>
                </th>
                <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5">Company</th>
                <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5">Domain</th>
                <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5">Model</th>
                <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5 text-right">Tokens</th>
                <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5 text-right">Cost</th>
                <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5 text-right">Latency</th>
                <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              <AnimatePresence mode="popLayout">
                {filteredLogs.map((log, idx) => (
                  <motion.tr 
                    layout
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    key={log.id || idx} 
                    className="hover:bg-white/[0.02] transition-colors group"
                  >
                    <td className="py-5 px-8">
                      <div className="flex flex-col">
                        <span className="text-white font-medium text-sm">
                          {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </span>
                        <span className="text-slate-500 text-xs mt-0.5">
                          {new Date(log.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </td>
                    <td className="py-5 px-8">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                          <Building2 className="w-4 h-4 text-indigo-400" />
                        </div>
                        <span className="text-white font-semibold text-sm">{log.company_name}</span>
                      </div>
                    </td>
                    <td className="py-5 px-8">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                        <span className="text-slate-300 text-xs font-bold uppercase tracking-wide px-2 py-1 rounded-md bg-cyan-500/10 border border-cyan-500/20">
                          {log.domain_name}
                        </span>
                      </div>
                    </td>
                    <td className="py-5 px-8">
                      <div className="flex items-center gap-2 text-slate-400 text-sm">
                        <Cpu className="w-4 h-4" />
                        {log.model_name}
                      </div>
                    </td>
                    <td className="py-5 px-8 text-right font-mono text-sm text-white font-bold">
                      {log.total_tokens?.toLocaleString()}
                    </td>
                    <td className="py-5 px-8 text-right font-mono text-sm text-emerald-400 font-bold">
                      ${parseFloat(log.estimated_cost).toFixed(4)}
                    </td>
                    <td className="py-5 px-8 text-right">
                      <div className="flex items-center justify-end gap-1.5 text-slate-400 text-sm font-mono">
                        <Clock className="w-3.5 h-3.5" />
                        {log.execution_time_ms}ms
                      </div>
                    </td>
                    <td className="py-5 px-8">
                      <StatusPill status={log.status || 'success'} />
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
        
        {filteredLogs.length === 0 && (
          <div className="py-20 text-center space-y-4">
            <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto">
              <Search className="w-8 h-8 text-slate-600" />
            </div>
            <p className="text-slate-500 font-medium text-lg">No matching records found for your search.</p>
          </div>
        )}

        <div className="p-6 bg-white/[0.01] border-t border-white/5 flex items-center justify-between">
          <p className="text-slate-500 text-sm">Showing <span className="text-white font-bold">{filteredLogs.length}</span> entries</p>
          <div className="flex gap-2">
            <button className="px-4 py-2 rounded-xl bg-white/5 border border-white/5 text-slate-400 text-sm font-bold hover:bg-white/10 transition-colors disabled:opacity-50" disabled>Previous</button>
            <button className="px-4 py-2 rounded-xl bg-white/5 border border-white/5 text-slate-300 text-sm font-bold hover:bg-white/10 transition-colors">Next</button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

const MetricCard = ({ title, value, trend, icon, data, color }) => {
  const isPositive = trend.startsWith('+');
  
  return (
    <motion.div 
      whileHover={{ y: -5 }}
      className="glass-card rounded-3xl p-6 border-white/5 relative overflow-hidden group"
    >
      <div className="relative z-10">
        <div className="flex items-center justify-between mb-6">
          <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:border-white/20 transition-colors">
            {icon}
          </div>
          <div className={cn(
            "flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full",
            isPositive ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
          )}>
            {isPositive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {trend}
          </div>
        </div>
        
        <div className="space-y-1">
          <p className="text-slate-400 text-sm font-bold uppercase tracking-wider">{title}</p>
          <div className="flex items-baseline gap-2">
            <h3 className="text-3xl font-black text-white">{value}</h3>
          </div>
        </div>

        <div className="mt-6 h-[60px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id={`color-${title}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={color} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={color} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke={color} 
                strokeWidth={3} 
                fillOpacity={1} 
                fill={`url(#color-${title})`} 
                animationDuration={2000}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      
      {/* Decorative background glow */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-32 h-32 rounded-full blur-[80px] opacity-20 group-hover:opacity-40 transition-opacity" style={{ backgroundColor: color }} />
    </motion.div>
  );
};

const StatusPill = ({ status }) => {
  const styles = {
    success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    error: "bg-red-500/10 text-red-400 border-red-500/20",
    failed: "bg-red-500/10 text-red-400 border-red-500/20",
  };

  const currentStyle = styles[status.toLowerCase()] || styles.success;

  return (
    <div className={cn("px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border w-fit", currentStyle)}>
      {status}
    </div>
  );
};

export default TokenDashboard;

