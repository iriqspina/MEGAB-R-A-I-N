using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Management;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

[assembly: AssemblyTitle("MegaBrain")]
[assembly: AssemblyProduct("MegaBrain Central")]
[assembly: AssemblyDescription("Abre a central MegaBrain desta instalação.")]
[assembly: AssemblyCompany("<USUARIO>")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

internal static class Launcher
{
    private const string AppId = "<USUARIO>.MegaBrain.Central";
    private static readonly string Bootstrap = AppDomain.CurrentDomain.BaseDirectory;
    private static readonly string App = Path.GetFullPath(Path.Combine(Bootstrap, ".."));
    private static readonly string Root = Path.GetFullPath(Path.Combine(App, "..", ".."));
    private static readonly string Entry = Path.Combine(App, "central_desktop.py");
    private static readonly string Runtime = Path.GetFullPath(Path.Combine(App, "..", "ia-quota-widget", ".venv", "Scripts", "pythonw.exe"));
    private static readonly string Executable = Path.Combine(Bootstrap, "MegaBrain.exe");
    private static readonly string Shortcut = Path.Combine(Root, "00_PARA-VOCE", "MegaBrain Central.lnk");
    private static readonly PropertyKey IdKey = new PropertyKey(new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);

    [STAThread]
    private static int Main(string[] args)
    {
        bool utility = args.Length > 0;
        try
        {
            SetCurrentProcessExplicitAppUserModelID(AppId);
            RequireFiles();
            if (args.Length == 1 && args[0] == "--create-shortcut") { CreateShortcut(); return 0; }
            if (args.Length == 1 && args[0] == "--verify") { Verify(); return 0; }
            if (utility) throw new ArgumentException("Argumento desconhecido. Nenhuma central foi iniciada.");
            using (Mutex gate = new Mutex(false, "Local\\<USUARIO>.MegaBrain.Central.Launcher"))
            {
                bool owns = false;
                try
                {
                    try { owns = gate.WaitOne(0); } catch (AbandonedMutexException) { owns = true; }
                    if (!owns) { Trace("Another launcher is starting; waiting without launching."); return WaitForWindow(null); }
                    List<int> running = RunningCentral();
                    Trace("Launch requested. Existing central process IDs: " + String.Join(",", running));
                    IntPtr window = FindWindow(running);
                    if (window != IntPtr.Zero) { Trace("Existing window found; focusing only."); Focus(window); return 0; }
                    // A Python wrapper and its child are one launch, not two instances.
                    // If startup is already in progress, do not start another interpreter.
                    if (running.Count > 0) { Trace("Central process exists without visible window; waiting without launching."); return WaitForWindow(null); }
                    ProcessStartInfo start = new ProcessStartInfo(Runtime, "\"" + Entry + "\"");
                    start.WorkingDirectory = App;
                    start.UseShellExecute = false;
                    start.CreateNoWindow = true;
                    using (Process child = Process.Start(start))
                    {
                        if (child == null) throw new InvalidOperationException("O Windows não iniciou a central.");
                        Trace("Started Python wrapper PID " + child.Id + ".");
                        return WaitForWindow(child);
                    }
                }
                finally { if (owns) gate.ReleaseMutex(); }
            }
        }
        catch (Exception ex)
        {
            Trace(ex.GetType().Name + ": " + ex.Message);
            if (!utility) MessageBox.Show("Não foi possível abrir o MegaBrain.\n\n" + ex.Message + "\n\nRegistro: " + Path.Combine(Bootstrap, "launcher.log"), "MegaBrain", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static void RequireFiles()
    {
        foreach (string file in new[] { Entry, Runtime, Path.Combine(App, "assets", "megabrain-cerebro-rosa.ico") })
            if (!File.Exists(file)) throw new FileNotFoundException("Arquivo necessário não encontrado: " + file);
    }

    private static List<int> RunningCentral()
    {
        List<int> ids = new List<int>();
        using (ManagementObjectSearcher query = new ManagementObjectSearcher("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name = 'python.exe' OR Name = 'pythonw.exe'"))
        using (ManagementObjectCollection results = query.Get())
            foreach (ManagementObject item in results)
            using (item)
            {
                string command = Convert.ToString(item["CommandLine"]);
                // Inspect locally; never log command lines or authentication data.
                if (command.IndexOf(Entry, StringComparison.OrdinalIgnoreCase) >= 0)
                    ids.Add(Convert.ToInt32(item["ProcessId"]));
            }
        return ids;
    }

    private static IntPtr FindWindow(List<int> ids)
    {
        IntPtr found = IntPtr.Zero;
        EnumWindows(delegate(IntPtr window, IntPtr parameter)
        {
            uint pid; GetWindowThreadProcessId(window, out pid);
            if (!ids.Contains((int)pid) || !IsWindowVisible(window)) return true;
            StringBuilder title = new StringBuilder(512);
            GetWindowText(window, title, title.Capacity);
            if (!title.ToString().StartsWith("MegaBrain", StringComparison.Ordinal)) return true;
            found = window; return false;
        }, IntPtr.Zero);
        return found;
    }

    private static void Trace(string message)
    {
        File.AppendAllText(Path.Combine(Bootstrap, "launcher.log"), DateTimeOffset.Now.ToString("o") + " " + message + Environment.NewLine, Encoding.UTF8);
    }

    private static int WaitForWindow(Process started)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(35);
        int absent = 0;
        while (DateTime.UtcNow < deadline)
        {
            List<int> running = RunningCentral();
            IntPtr window = FindWindow(running);
            if (window != IntPtr.Zero) { Trace("Central window found. Process IDs: " + String.Join(",", running)); Focus(window); return 0; }
            absent = running.Count == 0 ? absent + 1 : 0;
            if (absent >= 4)
            {
                if (started != null && started.HasExited)
                    throw new InvalidOperationException("O processo da central encerrou antes de abrir a janela (código " + started.ExitCode + "). Consulte data\\central-desktop.log.");
                if (started == null)
                    throw new InvalidOperationException("O processo anterior encerrou durante a espera. Nenhuma segunda cópia foi aberta; tente novamente.");
            }
            Thread.Sleep(350);
        }
        throw new InvalidOperationException("A janela ainda não respondeu. Outra cópia não foi aberta. Consulte também data\\central-desktop.log.");
    }

    private static void Focus(IntPtr window)
    {
        if (IsIconic(window)) ShowWindowAsync(window, 9);
        SetForegroundWindow(window);
    }

    private static object NewLink() { return Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("00021401-0000-0000-C000-000000000046"))); }

    private static void CreateShortcut()
    {
        if (File.Exists(Shortcut)) throw new IOException("O atalho já existe e foi preservado: " + Shortcut);
        Directory.CreateDirectory(Path.GetDirectoryName(Shortcut));
        object instance = NewLink();
        try
        {
            IShellLinkW link = (IShellLinkW)instance;
            link.SetPath(Executable);
            link.SetWorkingDirectory(App);
            link.SetDescription("MegaBrain Central — projetos, referências e resultados");
            link.SetIconLocation(Executable, 0);
            link.SetShowCmd(1);
            IPropertyStore store = (IPropertyStore)instance;
            PropertyKey key = IdKey;
            PropVariant value = PropVariant.String(AppId);
            try { store.SetValue(ref key, ref value); store.Commit(); }
            finally { PropVariantClear(ref value); }
            ((IPersistFile)instance).Save(Shortcut, true);
        }
        finally { Marshal.FinalReleaseComObject(instance); }
    }

    private static void Verify()
    {
        // This mode never launches, focuses, closes or pins any application.
        List<int> running = RunningCentral();
        string target = null, icon = null, workdir = null, id = null;
        int iconIndex = -1;
        if (File.Exists(Shortcut))
        {
            object instance = NewLink();
            try
            {
                ((IPersistFile)instance).Load(Shortcut, 0);
                IShellLinkW link = (IShellLinkW)instance;
                StringBuilder buffer = new StringBuilder(32768);
                link.GetPath(buffer, buffer.Capacity, IntPtr.Zero, 4); target = buffer.ToString();
                buffer.Clear(); link.GetWorkingDirectory(buffer, buffer.Capacity); workdir = buffer.ToString();
                buffer.Clear(); link.GetIconLocation(buffer, buffer.Capacity, out iconIndex); icon = buffer.ToString();
                PropertyKey key = IdKey; PropVariant value;
                ((IPropertyStore)instance).GetValue(ref key, out value);
                try { id = value.Type == 31 ? Marshal.PtrToStringUni(value.Pointer) : null; }
                finally { PropVariantClear(ref value); }
            }
            finally { Marshal.FinalReleaseComObject(instance); }
        }
        bool matches = String.Equals(target, Executable, StringComparison.OrdinalIgnoreCase) && String.Equals(workdir, App, StringComparison.OrdinalIgnoreCase) && id == AppId && String.Equals(icon, Executable, StringComparison.OrdinalIgnoreCase) && iconIndex == 0;
        var report = new { at = DateTimeOffset.Now.ToString("o"), mode = "read-only; no launch, focus or pin", runtime = Runtime, entry = Entry, executable = Executable, shortcut = Shortcut, shortcut_target = target, shortcut_icon = icon, shortcut_icon_index = iconIndex, shortcut_working_directory = workdir, shortcut_app_id = id, shortcut_matches = matches, existing_process_ids = running, existing_window_found = FindWindow(running) != IntPtr.Zero, taskbar_pinned = "NOT_ATTEMPTED", cold_launch = "NOT_TESTED" };
        string output = Path.Combine(Root, "evidence", "261011_app-megabrain", "launcher", "verification.json");
        Directory.CreateDirectory(Path.GetDirectoryName(output));
        File.WriteAllText(output, new JavaScriptSerializer().Serialize(report), Encoding.UTF8);
        if (!matches) throw new InvalidOperationException("A verificação do atalho falhou. Consulte evidence/261011_app-megabrain/launcher/verification.json.");
    }

    private delegate bool EnumWindowsProc(IntPtr window, IntPtr parameter);
    [DllImport("shell32.dll", CharSet = CharSet.Unicode)] private static extern int SetCurrentProcessExplicitAppUserModelID(string appId);
    [DllImport("ole32.dll")] private static extern int PropVariantClear(ref PropVariant value);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);
    [DllImport("user32.dll")] private static extern bool IsWindowVisible(IntPtr window);
    [DllImport("user32.dll")] private static extern bool IsIconic(IntPtr window);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] private static extern int GetWindowText(IntPtr window, StringBuilder text, int count);
    [DllImport("user32.dll")] private static extern bool ShowWindowAsync(IntPtr window, int command);
    [DllImport("user32.dll")] private static extern bool SetForegroundWindow(IntPtr window);

    [StructLayout(LayoutKind.Sequential)] private struct PropertyKey
    {
        public Guid Format; public uint Id;
        public PropertyKey(Guid format, uint id) { Format = format; Id = id; }
    }
    [StructLayout(LayoutKind.Explicit, Size = 24)] private struct PropVariant
    {
        [FieldOffset(0)] public ushort Type;
        [FieldOffset(8)] public IntPtr Pointer;
        public static PropVariant String(string value) { return new PropVariant { Type = 31, Pointer = Marshal.StringToCoTaskMemUni(value) }; }
    }
    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IPropertyStore
    {
        void GetCount(out uint count);
        void GetAt(uint index, out PropertyKey key);
        void GetValue(ref PropertyKey key, out PropVariant value);
        void SetValue(ref PropertyKey key, ref PropVariant value);
        void Commit();
    }
    [ComImport, Guid("000214F9-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IShellLinkW
    {
        void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int capacity, IntPtr data, uint flags);
        void GetIDList(out IntPtr list);
        void SetIDList(IntPtr list);
        void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder text, int capacity);
        void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string text);
        void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder directory, int capacity);
        void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string directory);
        void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder arguments, int capacity);
        void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string arguments);
        void GetHotkey(out short hotkey);
        void SetHotkey(short hotkey);
        void GetShowCmd(out int command);
        void SetShowCmd(int command);
        void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder icon, int capacity, out int index);
        void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string icon, int index);
        void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string path, uint reserved);
        void Resolve(IntPtr window, uint flags);
        void SetPath([MarshalAs(UnmanagedType.LPWStr)] string path);
    }
}
