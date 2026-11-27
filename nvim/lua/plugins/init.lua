return {
  -- 포맷터
  {
    "stevearc/conform.nvim",
    opts = require "configs.conform",
  },

  -- LSP 설정
  {
    "neovim/nvim-lspconfig",
    config = function()
      require("nvchad.configs.lspconfig").defaults()
      require "configs.lspconfig"
    end,
  },

  -- 구문 하이라이팅
  {
    "nvim-treesitter/nvim-treesitter",
    lazy = false,
    build = ":TSUpdate",
    config = function()
      pcall(function()
        dofile(vim.g.base46_cache .. "syntax")
        dofile(vim.g.base46_cache .. "treesitter")
      end)

      -- main 브랜치는 ensure_installed를 쓰지 않고 파서 빌드에 tree-sitter CLI가 필요합니다.
      if vim.fn.executable "tree-sitter" == 1 then
        require("nvim-treesitter").install { "vim", "lua", "vimdoc", "html", "css", "c", "cpp", "rust" }
      end

      vim.api.nvim_create_autocmd("FileType", {
        callback = function(args)
          pcall(vim.treesitter.start, args.buf)
        end,
      })
    end,
  },

  -- 디버거 (DAP)
  {
    "mfussenegger/nvim-dap",
    config = function()
      local dap = require "dap"
      dap.adapters.codelldb = {
        type = "server",
        port = "${port}",
        executable = {
          command = "codelldb",
          args = { "--port", "${port}" },
        },
      }
      local config = {
        {
          name = "Launch file",
          type = "codelldb",
          request = "launch",
          program = function()
            return vim.fn.input("Executable path: ", vim.fn.getcwd() .. "/", "file")
          end,
          cwd = "${workspaceFolder}",
          stopOnEntry = false,
        },
      }
      dap.configurations.c = config
      dap.configurations.cpp = config
      dap.configurations.rust = config
    end,
  },

  {
    "rcarriga/nvim-dap-ui",
    dependencies = { "mfussenegger/nvim-dap", "nvim-neotest/nvim-nio" },
    cmd = { "DapContinue", "DapToggleBreakpoint", "DapStepOver", "DapStepInto", "DapStepOut", "DapTerminate" },
    keys = {
      { "<F5>", "<cmd>DapContinue<CR>", desc = "DAP continue" },
      { "<F10>", "<cmd>DapStepOver<CR>", desc = "DAP step over" },
      { "<F11>", "<cmd>DapStepInto<CR>", desc = "DAP step into" },
      { "<F12>", "<cmd>DapStepOut<CR>", desc = "DAP step out" },
      { "<leader>db", "<cmd>DapToggleBreakpoint<CR>", desc = "DAP toggle breakpoint" },
    },
    config = function()
      local dap, dapui = require "dap", require "dapui"
      dapui.setup()
      dap.listeners.after.event_initialized["dapui_config"] = function() dapui.open() end
      dap.listeners.before.event_terminated["dapui_config"] = function() dapui.close() end
      dap.listeners.before.event_exited["dapui_config"] = function() dapui.close() end
    end,
  },

  -- [Rider 스타일] Git 코드 좌측 표시 & 실시간 Blame (작성자/커밋 표시)
  {
    "lewis6991/gitsigns.nvim",
    event = "User FilePost",
    opts = {
      signs = {
        add          = { text = "▎" },
        change       = { text = "▎" },
        delete       = { text = "" },
        topdelete    = { text = "" },
        changedelete = { text = "▎" },
      },
      current_line_blame = true, -- 현재 줄에 Rider처럼 작성자/커밋 메시지 연하게 표시
      current_line_blame_opts = {
        delay = 300,
      },
    },
  },

  -- [Rider 스타일] Git 커밋/Diff 시각화 툴 (Diffview)
  {
    "sindrets/diffview.nvim",
    cmd = { "DiffviewOpen", "DiffviewFileHistory" },
  },

  -- [Rider 스타일] 전용 Git UI (LazyGit)
  {
    "kdheepak/lazygit.nvim",
    cmd = {
      "LazyGit",
      "LazyGitConfig",
      "LazyGitCurrentFile",
      "LazyGitFilter",
      "LazyGitFilterCurrentFile",
    },
    dependencies = {
      "nvim-lua/plenary.nvim",
    },
  },
}
